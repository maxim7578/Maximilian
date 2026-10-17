import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

// Fonts ship as woff2 files in public/fonts (from Fontsource, SIL OFL 1.1) so
// renders never fetch from fonts.gstatic.com. That keeps rendering working
// offline and behind proxies that the render browser does not use.

type FontStyle = "normal" | "italic";

const loadLocalFamily = (
  family: string,
  filePrefix: string,
  style: FontStyle,
  weights: string[],
): { fontFamily: string } => {
  // loadFont() holds the render via delayRender() and cancels it on failure.
  for (const weight of weights) {
    void loadFont({
      family,
      url: staticFile(`fonts/${filePrefix}-latin-${weight}-${style}.woff2`),
      weight,
      style,
    });
  }
  return { fontFamily: family };
};

export const loadSpaceGrotesk = (weights: string[]) =>
  loadLocalFamily("Space Grotesk", "space-grotesk", "normal", weights);

export const loadPlayfairDisplay = (style: FontStyle, weights: string[]) =>
  loadLocalFamily("Playfair Display", "playfair-display", style, weights);
