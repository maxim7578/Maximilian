// Evaluate remotion/no-react before any delayRender() call below. Its module
// init resets window.remotion_delayRenderHandles; if it first runs later (via
// @remotion/transitions), it drops handles registered here and the render
// times out even though the fonts loaded.
import "remotion/no-react";
import { continueRender, delayRender, staticFile } from "remotion";

// Fonts ship as woff2 files in public/fonts (from Fontsource, SIL OFL 1.1) so
// renders never fetch from fonts.gstatic.com. That keeps rendering working
// offline and behind proxies that the render browser does not use.
//
// Mirrors the loading strategy of @remotion/google-fonts: each face is loaded
// once per page (several compositions request the same weights), a stalled
// load times out and is retried, and the render waits via delayRender().

type FontStyle = "normal" | "italic";

const LOAD_TIMEOUT_MS = 18000;
const RETRIES = 2;

const loadedFaces: Record<string, Promise<void> | undefined> = {};

const loadWithTimeout = (face: FontFace): Promise<void> => {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(
      () => reject(new Error(`Timed out loading font ${face.family}`)),
      LOAD_TIMEOUT_MS,
    );
  });
  return Promise.race([
    face.load().then(() => {
      clearTimeout(timer);
    }),
    timeout,
  ]);
};

const loadFace = (
  family: string,
  url: string,
  weight: string,
  style: FontStyle,
): void => {
  if (typeof FontFace === "undefined") {
    return;
  }
  const key = `${family}-${style}-${weight}`;
  if (loadedFaces[key]) {
    return;
  }

  const handle = delayRender(`Loading local font ${key}`, {
    timeoutInMilliseconds: 60000,
  });

  const attempt = (retriesLeft: number): Promise<void> => {
    const face = new FontFace(family, `url('${url}') format('woff2')`, {
      weight,
      style,
    });
    return loadWithTimeout(face)
      .then(() => {
        document.fonts.add(face);
        continueRender(handle);
      })
      .catch((err) => {
        if (retriesLeft === 0) {
          loadedFaces[key] = undefined;
          throw err;
        }
        return attempt(retriesLeft - 1);
      });
  };

  loadedFaces[key] = attempt(RETRIES);
};

const loadLocalFamily = (
  family: string,
  filePrefix: string,
  style: FontStyle,
  weights: string[],
): { fontFamily: string } => {
  for (const weight of weights) {
    loadFace(
      family,
      staticFile(`fonts/${filePrefix}-latin-${weight}-${style}.woff2`),
      weight,
      style,
    );
  }
  return { fontFamily: family };
};

export const loadSpaceGrotesk = (weights: string[]) =>
  loadLocalFamily("Space Grotesk", "space-grotesk", "normal", weights);

export const loadPlayfairDisplay = (style: FontStyle, weights: string[]) =>
  loadLocalFamily("Playfair Display", "playfair-display", style, weights);
