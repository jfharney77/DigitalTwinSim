import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "../src/tokens.css";
import "../src/skin.css";
import "../src/shell.css";
import "./gallery.css";
import { Gallery } from "./Gallery";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Gallery />
  </StrictMode>,
);
