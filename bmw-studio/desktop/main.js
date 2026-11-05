// BimmerVision Cockpit – Electron-Hauptprozess.
// Laedt die offline-Oberflaeche. Kein Internet, kein Node im Fenster, nur lesende Demo.
const { app, BrowserWindow, Menu, shell } = require("electron");
const path = require("path");

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 500,
    minWidth: 900,
    minHeight: 380,
    backgroundColor: "#04060b",
    autoHideMenuBar: true,
    title: "BimmerVision Cockpit",
    icon: path.join(__dirname, "icon.png"),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
    },
  });

  Menu.setApplicationMenu(null);
  win.loadFile("app.html");

  // Externe Links im Standardbrowser oeffnen, nicht im App-Fenster.
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:/.test(url)) shell.openExternal(url);
    return { action: "deny" };
  });
}

app.whenReady().then(() => {
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
