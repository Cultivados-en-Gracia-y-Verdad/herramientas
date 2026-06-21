import React from "react";
import ReactDOM from "react-dom/client";
import { applyTheme, loadThemePreference } from "./lib/theme";
import App from "./App";

applyTheme(loadThemePreference());

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
