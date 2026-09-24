/**
 * icons.js — Ícones circulares e shapes decorativos para o deck PFC
 * Todos os ícones são construídos com shapes nativos do pptxgenjs,
 * sem dependência de arquivo externo.
 */

"use strict";

// ── Paleta ──────────────────────────────────────────────────────────
const C = {
  NAVY:    "1a3a5c",
  GOLD:    "C9A227",
  STEEL:   "7B8FA1",
  SLATE:   "4A5568",
  WHITE:   "FFFFFF",
  LIGHT:   "F0F2F5",
  SUCCESS: "2E7D32",
  ALERT:   "C62828",
  INFO:    "1565C0",
  SHADOW:  "C8D0DA",
};

/**
 * Adiciona um badge circular com ícone texto (emoji ou letra) em um slide.
 * @param {Object} slide  - slide pptxgenjs
 * @param {string} symbol - caractere/emoji de exibição
 * @param {number} x, y   - posição em inches
 * @param {number} size   - diâmetro em inches (default 0.55)
 * @param {string} bg     - cor de fundo hex (default NAVY)
 * @param {string} fg     - cor do texto hex (default GOLD)
 */
function iconBadge(slide, symbol, x, y, size = 0.55, bg = C.NAVY, fg = C.GOLD) {
  // sombra
  slide.addShape("ellipse", {
    x: x + 0.03, y: y + 0.03, w: size, h: size,
    fill: { color: C.SHADOW }, line: { color: C.SHADOW },
  });
  // círculo principal
  slide.addShape("ellipse", {
    x, y, w: size, h: size,
    fill: { color: bg }, line: { color: bg },
  });
  // símbolo
  slide.addText(symbol, {
    x, y: y + size * 0.1, w: size, h: size * 0.8,
    fontSize: Math.round(size * 18),
    bold: true, color: fg, align: "center", valign: "middle",
    fontFace: "Calibri",
  });
}

/**
 * Seta direcional (→) como shape retangular estreito.
 * @param {Object} slide
 * @param {number} x, y - posição
 * @param {number} w    - largura da seta
 * @param {string} color
 */
function arrow(slide, x, y, w = 0.4, color = C.GOLD) {
  slide.addShape("rightArrow", {
    x, y, w, h: 0.25,
    fill: { color }, line: { color },
  });
}

/**
 * Linha horizontal decorativa (separador de seção).
 * @param {Object} slide
 * @param {number} x, y, w
 * @param {string} color
 * @param {number} size   - espessura em pt
 */
function hRule(slide, x, y, w, color = C.GOLD, size = 2) {
  slide.addShape("line", {
    x, y, w, h: 0,
    line: { color, width: size },
  });
}

/**
 * Retângulo decorativo de acento (barra lateral esquerda de card).
 */
function accentBar(slide, x, y, h, color = C.GOLD) {
  slide.addShape("rect", {
    x, y, w: 0.06, h,
    fill: { color }, line: { color: "none" },
  });
}

module.exports = { C, iconBadge, arrow, hRule, accentBar };
