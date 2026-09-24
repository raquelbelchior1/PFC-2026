/**
 * build.js â€” Gerador da ApresentaÃ§Ã£o PFC: CaixÃ£o de Areia com Realidade Aumentada
 * VerificaÃ§Ã£o de Curso (VC) â€” AMAN 2026
 *
 * Paleta: NAVY #1a3a5c | GOLD #C9A227 | STEEL #7B8FA1 | LIGHT #F0F2F5
 * TÃ­tulos: Cambria Bold | Corpo: Calibri
 * Cards com sombra e cantos arredondados via shadow shape + fill
 */

"use strict";

const PptxGenJS = require("pptxgenjs");
const { C, iconBadge, arrow, hRule, accentBar } = require("./icons.js");

const pptx = new PptxGenJS();
pptx.layout = "LAYOUT_WIDE"; // 13.33 Ã— 7.5 inches

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// HELPERS GLOBAIS
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

/** Fundo texturizado padrÃ£o (gradiente azul Navy para NAVY-dark) */
function bgTexture(slide, light = false) {
  slide.background = { color: light ? C.LIGHT : "0f2540" };
  if (!light) {
    // faixa decorativa dourada no topo
    slide.addShape("rect", {
      x: 0, y: 0, w: 13.33, h: 0.08,
      fill: { color: C.GOLD }, line: { type: "none" },
    });
  }
}

/** CabeÃ§alho padrÃ£o de slide interno */
function header(slide, title, subtitle = "") {
  // fundo de cabeÃ§alho
  slide.addShape("rect", {
    x: 0, y: 0, w: 13.33, h: 1.15,
    fill: { color: C.NAVY }, line: { type: "none" },
  });
  // barra dourada
  slide.addShape("rect", {
    x: 0, y: 1.15, w: 13.33, h: 0.06,
    fill: { color: C.GOLD }, line: { type: "none" },
  });
  // tÃ­tulo
  slide.addText(title, {
    x: 0.35, y: 0.1, w: 12.0, h: 0.65,
    fontFace: "Cambria", fontSize: 26, bold: true,
    color: C.WHITE, align: "left", valign: "middle",
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.35, y: 0.72, w: 12.0, h: 0.38,
      fontFace: "Calibri", fontSize: 13, italic: true,
      color: C.GOLD, align: "left", valign: "middle",
    });
  }
}

/** RodapÃ© de marca */
function footerBrand(slide, pageNum = "") {
  slide.addShape("rect", {
    x: 0, y: 7.28, w: 13.33, h: 0.22,
    fill: { color: C.NAVY }, line: { type: "none" },
  });
  slide.addText("PFC â€” CaixÃ£o de Areia com Realidade Aumentada  |  AMAN 2026", {
    x: 0.2, y: 7.28, w: 11.5, h: 0.22,
    fontFace: "Calibri", fontSize: 8, color: C.STEEL, align: "left", valign: "middle",
  });
  if (pageNum) {
    slide.addText(pageNum, {
      x: 12.8, y: 7.28, w: 0.5, h: 0.22,
      fontFace: "Calibri", fontSize: 8, color: C.GOLD, align: "right", valign: "middle",
    });
  }
}

/** Card com sombra, borda arredondada e barra de acento dourada */
function bulletCard(slide, title, bullets, x, y, w, h, opts = {}) {
  const bg = opts.bg || C.WHITE;
  const accent = opts.accent || C.GOLD;
  const icon = opts.icon || "";
  // sombra
  slide.addShape("rect", {
    x: x + 0.05, y: y + 0.05, w, h,
    fill: { color: C.SHADOW || "C8D0DA" }, line: { type: "none" },
    rectRadius: 0.08,
  });
  // card
  slide.addShape("rect", {
    x, y, w, h,
    fill: { color: bg }, line: { color: C.STEEL, width: 0.5 },
    rectRadius: 0.08,
  });
  // barra de acento
  slide.addShape("rect", {
    x, y, w: 0.07, h,
    fill: { color: accent }, line: { type: "none" },
    rectRadius: 0.04,
  });
  // tÃ­tulo do card
  let titleX = x + 0.18;
  if (icon) {
    iconBadge(slide, icon, x + 0.18, y + 0.1, 0.38, accent === C.GOLD ? C.NAVY : C.NAVY, C.GOLD);
    titleX = x + 0.66;
  }
  slide.addText(title, {
    x: titleX, y: y + 0.1, w: w - (titleX - x) - 0.1, h: 0.3,
    fontFace: "Cambria", fontSize: 12, bold: true,
    color: C.NAVY, align: "left", valign: "middle",
  });
  // bullets
  const bulletRows = bullets.map(b => ({
    text: b,
    options: {
      fontFace: "Calibri", fontSize: 10.5, color: C.SLATE,
      bullet: { type: "bullet", indent: 10 }, breakLine: true,
    },
  }));
  slide.addText(bulletRows, {
    x: x + 0.18, y: y + 0.45, w: w - 0.28, h: h - 0.55,
    valign: "top", paraSpaceAfter: 3,
  });
}

/** Divisor de seÃ§Ã£o (slide de transiÃ§Ã£o colorido) */
function sectionDivider(slide, part, title, subtitle = "") {
  slide.background = { color: C.NAVY };
  // faixa dourada esquerda
  slide.addShape("rect", {
    x: 0, y: 0, w: 0.18, h: 7.5,
    fill: { color: C.GOLD }, line: { type: "none" },
  });
  // parte/nÃºmero
  slide.addText(part, {
    x: 0.4, y: 2.2, w: 12.5, h: 0.5,
    fontFace: "Calibri", fontSize: 14, italic: true, color: C.GOLD, align: "left",
  });
  // tÃ­tulo grande
  slide.addText(title, {
    x: 0.4, y: 2.65, w: 12.5, h: 1.2,
    fontFace: "Cambria", fontSize: 36, bold: true, color: C.WHITE, align: "left",
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.4, y: 3.85, w: 12.5, h: 0.5,
      fontFace: "Calibri", fontSize: 15, color: C.STEEL, align: "left",
    });
  }
  hRule(slide, 0.4, 4.4, 5.0, C.GOLD, 2);
}

/** Placeholder de foto (borda tracejada) */
function photoPlaceholder(slide, x, y, w, h, label) {
  // fundo cinza claro
  slide.addShape("rect", {
    x, y, w, h,
    fill: { color: C.LIGHT },
    line: { color: C.STEEL, width: 1.5, dashType: "dash" },
    rectRadius: 0.06,
  });
  // Ã­cone cÃ¢mera (texto)
  slide.addText("ðŸ“·", {
    x, y: y + h * 0.2, w, h: h * 0.45,
    fontFace: "Calibri", fontSize: 28, align: "center", valign: "bottom",
  });
  // label em itÃ¡lico
  slide.addText(label, {
    x: x + 0.1, y: y + h * 0.62, w: w - 0.2, h: h * 0.32,
    fontFace: "Calibri", fontSize: 9, italic: true,
    color: C.STEEL, align: "center", valign: "top",
  });
}

/** NÃºmero de pÃ¡gina */
function pageNum(slide, n) {
  footerBrand(slide, String(n));
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 1 â€” CAPA
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  s.background = { color: "0f2540" };
  // faixa dourada topo
  s.addShape("rect", { x: 0, y: 0, w: 13.33, h: 0.12, fill: { color: C.GOLD }, line: { type: "none" } });
  // faixa dourada base
  s.addShape("rect", { x: 0, y: 7.38, w: 13.33, h: 0.12, fill: { color: C.GOLD }, line: { type: "none" } });
  // bloco central
  s.addShape("rect", { x: 0.5, y: 1.0, w: 12.33, h: 5.4, fill: { color: C.NAVY }, line: { color: C.GOLD, width: 1 }, rectRadius: 0.12 });
  // verificaÃ§Ã£o de curso badge
  s.addShape("rect", { x: 4.5, y: 1.3, w: 4.33, h: 0.45, fill: { color: C.GOLD }, line: { type: "none" }, rectRadius: 0.06 });
  s.addText("VERIFICAÃ‡ÃƒO DE CURSO", {
    x: 4.5, y: 1.3, w: 4.33, h: 0.45,
    fontFace: "Calibri", fontSize: 13, bold: true, color: C.NAVY, align: "center", valign: "middle",
  });
  // tÃ­tulo principal
  s.addText("CaixÃ£o de Areia com Realidade Aumentada", {
    x: 0.7, y: 1.85, w: 11.93, h: 1.05,
    fontFace: "Cambria", fontSize: 32, bold: true, color: C.WHITE, align: "center",
  });
  // subtÃ­tulo
  s.addText("Sistema de Baixo Custo Computacional para Apoio Ã  InstruÃ§Ã£o Militar", {
    x: 0.7, y: 2.88, w: 11.93, h: 0.55,
    fontFace: "Calibri", fontSize: 16, italic: true, color: C.GOLD, align: "center",
  });
  hRule(s, 2.0, 3.52, 9.33, C.GOLD, 1);
  // curso
  s.addText("Trabalho de ConclusÃ£o de Curso â€” Engenharia de ComputaÃ§Ã£o e EletrÃ´nica", {
    x: 0.7, y: 3.65, w: 11.93, h: 0.38,
    fontFace: "Calibri", fontSize: 13, color: C.STEEL, align: "center",
  });
  // integrantes
  s.addText("Cadetes: Raquel  Â·  Integrante 2  Â·  Integrante 3  Â·  Integrante 4", {
    x: 0.7, y: 4.08, w: 11.93, h: 0.35,
    fontFace: "Calibri", fontSize: 12, color: C.WHITE, align: "center",
  });
  s.addText("Orientador: Prof. [Nome do Orientador]", {
    x: 0.7, y: 4.43, w: 11.93, h: 0.3,
    fontFace: "Calibri", fontSize: 12, color: C.STEEL, align: "center",
  });
  // seÃ§Ã£o de simulaÃ§Ã£o
  s.addText("SeÃ§Ã£o de SimulaÃ§Ã£o â€” Academia Militar das Agulhas Negras â€” Julho 2026", {
    x: 0.7, y: 4.9, w: 11.93, h: 0.3,
    fontFace: "Calibri", fontSize: 11, color: C.GOLD, align: "center",
  });
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 2 â€” AGENDA
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  header(s, "Estrutura da ApresentaÃ§Ã£o");
  s.background = { color: C.LIGHT };
  header(s, "Estrutura da ApresentaÃ§Ã£o", "VC â€” VerificaÃ§Ã£o de Curso");
  footerBrand(s, "2");

  const items = [
    { n: "1", label: "Engenharia de ComputaÃ§Ã£o", subs: ["Arquitetura de Software", "Motor MatemÃ¡tico e Algoritmos", "OtimizaÃ§Ã£o de Desempenho (2,57Ã—)", "Qualidade e TDD â€” 59 testes", "Interface e Guia de ExecuÃ§Ã£o"], color: C.NAVY },
    { n: "2", label: "Engenharia EletrÃ´nica", subs: ["AdaptaÃ§Ã£o do Kinect", "SoluÃ§Ã£o de ProjeÃ§Ã£o: Espelho Refletor  â˜… NOVO", "Novo CaixÃ£o de Areia  â˜… NOVO"], color: C.INFO },
    { n: "3", label: "Resultados e PrÃ³ximos Passos", subs: ["Estado Atual do Sistema", "Desafios em Aberto", "Roadmap e Cronograma"], color: C.SUCCESS },
  ];

  items.forEach((item, i) => {
    const y = 1.4 + i * 1.85;
    // sombra
    s.addShape("rect", { x: 0.55, y: y + 0.05, w: 12.23, h: 1.65, fill: { color: C.SHADOW || "C8D0DA" }, line: { type: "none" }, rectRadius: 0.08 });
    // card
    s.addShape("rect", { x: 0.5, y, w: 12.23, h: 1.65, fill: { color: C.WHITE }, line: { color: item.color, width: 0.5 }, rectRadius: 0.08 });
    // acento lateral
    s.addShape("rect", { x: 0.5, y, w: 0.07, h: 1.65, fill: { color: item.color }, line: { type: "none" }, rectRadius: 0.04 });
    // nÃºmero
    s.addShape("ellipse", { x: 0.72, y: y + 0.58, w: 0.48, h: 0.48, fill: { color: item.color }, line: { type: "none" } });
    s.addText(item.n, { x: 0.72, y: y + 0.58, w: 0.48, h: 0.48, fontFace: "Cambria", fontSize: 16, bold: true, color: C.WHITE, align: "center", valign: "middle" });
    // tÃ­tulo
    s.addText(`Parte ${item.n} â€” ${item.label}`, { x: 1.32, y: y + 0.12, w: 10.8, h: 0.38, fontFace: "Cambria", fontSize: 14, bold: true, color: item.color, align: "left" });
    // subs
    s.addText(item.subs.join("   Â·   "), { x: 1.32, y: y + 0.52, w: 10.8, h: 0.85, fontFace: "Calibri", fontSize: 10.5, color: C.SLATE, align: "left", valign: "top", wrap: true });
  });
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 3 â€” DIVISOR PARTE 1: ENG. COMPUTAÃ‡ÃƒO
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  sectionDivider(s, "PARTE 1", "Engenharia de ComputaÃ§Ã£o", "Arquitetura Â· Motor MatemÃ¡tico Â· OtimizaÃ§Ã£o Â· Qualidade Â· Interface");
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 4 â€” ARQUITETURA DE SOFTWARE
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  s.background = { color: C.LIGHT };
  header(s, "Arquitetura de Software", "SeparaÃ§Ã£o estrita de responsabilidades em trÃªs camadas");
  footerBrand(s, "4");

  // diagrama de arquitetura
  const layers = [
    { label: "main.py", sub: "Orquestrador Â· MÃ¡quina de Estados Â· GUI (CustomTkinter)", color: C.GOLD, y: 1.4 },
    { label: "kinect_sensor.py", sub: "Hardware + Fallback em Cascata (Kinect v2 â†’ v1 â†’ SimulaÃ§Ã£o)", color: C.NAVY, y: 2.65 },
    { label: "motor_caixao_areia.py", sub: "Ãlgebra Linear Pura â€” RANSAC Â· SVD Â· Gram-Schmidt Â· Tsai", color: C.NAVY, y: 2.65 },
    { label: "mde_cartografia.py", sub: "GeoTIFF Real Â· Cubo Central Â· Morro Gaussiano (fallback)", color: C.NAVY, y: 2.65 },
  ];

  // camada orquestradora
  s.addShape("rect", { x: 0.6, y: 1.4, w: 12.13, h: 0.85, fill: { color: C.GOLD }, line: { type: "none" }, rectRadius: 0.07 });
  s.addText("main.py â€” Orquestrador / MÃ¡quina de Estados / GUI (CustomTkinter)", { x: 0.7, y: 1.4, w: 12.0, h: 0.85, fontFace: "Cambria", fontSize: 13, bold: true, color: C.NAVY, align: "center", valign: "middle" });

  // seta para baixo
  s.addShape("downArrow", { x: 6.29, y: 2.32, w: 0.75, h: 0.28, fill: { color: C.STEEL }, line: { type: "none" } });

  // trÃªs camadas inferiores
  const cols = [
    { x: 0.6, label: "kinect_sensor.py", sub: "Hardware + Fallback em Cascata\nKinect v2 â†’ Open3D â†’ Kinect v1 â†’ SimulaÃ§Ã£o", icon: "ðŸ“¡", color: C.STEEL },
    { x: 4.71, label: "motor_caixao_areia.py", sub: "Ãlgebra Linear Pura\nRANSAC Â· SVD Â· Gram-Schmidt Â· Tsai Â· Grade", icon: "ðŸ§®", color: C.NAVY },
    { x: 8.82, label: "mde_cartografia.py", sub: "Modelo Digital de ElevaÃ§Ã£o\nGeoTIFF Real Â· Cubo Central Â· Gaussiano", icon: "ðŸ—º", color: C.INFO },
  ];
  cols.forEach(col => {
    s.addShape("rect", { x: col.x + 0.04, y: 2.67, w: 3.98, h: 2.55, fill: { color: C.SHADOW || "C8D0DA" }, line: { type: "none" }, rectRadius: 0.07 });
    s.addShape("rect", { x: col.x, y: 2.62, w: 3.98, h: 2.55, fill: { color: C.WHITE }, line: { color: col.color, width: 1 }, rectRadius: 0.07 });
    s.addShape("rect", { x: col.x, y: 2.62, w: 3.98, h: 0.07, fill: { color: col.color }, line: { type: "none" }, rectRadius: 0.04 });
    s.addText(col.icon, { x: col.x, y: 2.7, w: 3.98, h: 0.55, fontFace: "Calibri", fontSize: 22, align: "center" });
    s.addText(col.label, { x: col.x + 0.1, y: 3.25, w: 3.78, h: 0.4, fontFace: "Cambria", fontSize: 11, bold: true, color: col.color, align: "center" });
    s.addText(col.sub, { x: col.x + 0.15, y: 3.65, w: 3.68, h: 1.4, fontFace: "Calibri", fontSize: 10, color: C.SLATE, align: "center", valign: "top", wrap: true });
  });

  // princÃ­pio chave
  s.addShape("rect", { x: 0.6, y: 5.35, w: 12.13, h: 0.55, fill: { color: C.NAVY }, line: { type: "none" }, rectRadius: 0.06 });
  s.addText("PrincÃ­pio: SeparaÃ§Ã£o estrita â€” nenhuma dependÃªncia cruzada entre hardware, lÃ³gica matemÃ¡tica e dados  |  TestÃ¡vel em isolamento", {
    x: 0.7, y: 5.35, w: 12.0, h: 0.55, fontFace: "Calibri", fontSize: 11, color: C.GOLD, align: "center", valign: "middle",
  });
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 5 â€” MOTOR MATEMÃTICO
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  s.background = { color: C.LIGHT };
  header(s, "Motor MatemÃ¡tico", "Pipeline completo: Kinect â†’ nuvem 3D â†’ plano â†’ base â†’ grade â†’ projeÃ§Ã£o");
  footerBrand(s, "5");

  const steps = [
    { n: "1", title: "Back-Projection Pinhole", body: "Profundidade (mm) â†’ nuvem 3D\nConvenÃ§Ã£o: Z_mesa negativo (fundo do caixÃ£o)", icon: "ðŸ“" },
    { n: "2", title: "Ajuste de Plano (RANSAC + SVD)", body: "1000 iter Â· limiar 3 cm\nIsola tampa, descarta moldura/piso/ruÃ­do", icon: "âœ‚" },
    { n: "3", title: "Gram-Schmidt + Matriz 4Ã—4", body: "Base ortonormal da mesa\nT_final salvo em calibration_data.json", icon: "ðŸ”„" },
    { n: "4", title: "DiscretizaÃ§Ã£o em Grade 30Ã—30", body: "900 cÃ©lulas de 5 cm Ã— 5 cm\nAltura mÃ©dia por cÃ©lula filtra ruÃ­do", icon: "ðŸ”²" },
    { n: "5", title: "ProjeÃ§Ã£o Tsai (cv2.projectPoints)", body: "961 vÃ©rtices projetados em lote\nSem chamadas individuais por cÃ©lula", icon: "ðŸŽ¯" },
    { n: "6", title: "RasterizaÃ§Ã£o (cv2.fillPoly)", body: "MÃ¡x. 3 chamadas por frame\nAgrupamento por cor (V/A/V)", icon: "ðŸŽ¨" },
  ];

  steps.forEach((st, i) => {
    const col = i % 3;
    const row = Math.floor(i / 3);
    const x = 0.35 + col * 4.34;
    const y = 1.42 + row * 2.82;
    // sombra
    s.addShape("rect", { x: x + 0.04, y: y + 0.04, w: 4.1, h: 2.55, fill: { color: C.SHADOW || "C8D0DA" }, line: { type: "none" }, rectRadius: 0.07 });
    // card
    s.addShape("rect", { x, y, w: 4.1, h: 2.55, fill: { color: C.WHITE }, line: { color: C.STEEL, width: 0.5 }, rectRadius: 0.07 });
    // nÃºmero badge
    s.addShape("ellipse", { x: x + 0.18, y: y + 0.15, w: 0.45, h: 0.45, fill: { color: C.NAVY }, line: { type: "none" } });
    s.addText(st.n, { x: x + 0.18, y: y + 0.15, w: 0.45, h: 0.45, fontFace: "Cambria", fontSize: 14, bold: true, color: C.GOLD, align: "center", valign: "middle" });
    // Ã­cone
    s.addText(st.icon, { x: x + 0.7, y: y + 0.12, w: 0.55, h: 0.5, fontFace: "Calibri", fontSize: 18, align: "left" });
    // tÃ­tulo
    s.addText(st.title, { x: x + 0.18, y: y + 0.65, w: 3.78, h: 0.45, fontFace: "Cambria", fontSize: 11.5, bold: true, color: C.NAVY, align: "left" });
    // acento
    s.addShape("rect", { x, y, w: 0.07, h: 2.55, fill: { color: C.GOLD }, line: { type: "none" }, rectRadius: 0.04 });
    // corpo
    s.addText(st.body, { x: x + 0.18, y: y + 1.12, w: 3.78, h: 1.35, fontFace: "Calibri", fontSize: 10.5, color: C.SLATE, valign: "top", wrap: true });
  });
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 6 â€” AJUSTE DE PLANO (RANSAC / SVD)
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  s.background = { color: C.LIGHT };
  header(s, "Ajuste de Plano â€” RANSAC + SVD", "CalibraÃ§Ã£o robusta da tampa plana com rejeiÃ§Ã£o de outliers (moldura, piso, ruÃ­do)");
  footerBrand(s, "6");

  // diagrama visual
  s.addText("Campo de VisÃ£o do Kinect", { x: 0.35, y: 1.35, w: 5.5, h: 0.3, fontFace: "Calibri", fontSize: 10, italic: true, color: C.STEEL, align: "center" });

  // FOV trapÃ©zio simplificado via rect
  s.addShape("trapezoid", { x: 0.5, y: 1.65, w: 5.2, h: 2.8, fill: { color: "E8EDF5" }, line: { color: C.STEEL, width: 1 } });
  s.addText("Tampa plana (inliers)\nZ_real â‰ˆ cte", { x: 1.2, y: 2.45, w: 2.8, h: 0.7, fontFace: "Calibri", fontSize: 10, color: C.NAVY, align: "center", bold: true });
  s.addShape("rect", { x: 1.0, y: 3.1, w: 3.2, h: 0.5, fill: { color: C.NAVY }, line: { type: "none" } });
  s.addText("Moldura / piso / ruÃ­do (outliers descartados)", { x: 0.5, y: 3.68, w: 5.2, h: 0.3, fontFace: "Calibri", fontSize: 9.5, italic: true, color: C.ALERT, align: "center" });

  // seta
  arrow(s, 5.85, 2.7, 0.45, C.GOLD);

  // colunas de passos
  const passos = [
    { title: "1. RANSAC", body: "1.000 iteraÃ§Ãµes\nLimiar: 3 cm\nViÃ©s Gaussiano para o centro\nIsola plano dominante (tampa)", color: C.NAVY },
    { title: "2. SVD sobre Inliers", body: "Menor valor singular â†’ normal\nRefinamento apenas sobre\nos pontos aprovados pelo RANSAC", color: C.INFO },
    { title: "3. Gram-Schmidt", body: "Z_mesa = normal\nX_mesa = Gram-Schmidt(semente, Z)\nY_mesa = Z Ã— X\nBase ortonormal completa", color: C.SUCCESS },
    { title: "4. Cache JSON", body: "T_final (4Ã—4) salvo em\ncalibration_data.json\nReutilizado nas prÃ³ximas\nexecuÃ§Ãµes automaticamente", color: C.GOLD },
  ];
  passos.forEach((p, i) => {
    const x = 6.45 + (i % 2) * 3.35;
    const y = 1.42 + Math.floor(i / 2) * 2.8;
    s.addShape("rect", { x: x + 0.04, y: y + 0.04, w: 3.15, h: 2.55, fill: { color: C.SHADOW || "C8D0DA" }, line: { type: "none" }, rectRadius: 0.07 });
    s.addShape("rect", { x, y, w: 3.15, h: 2.55, fill: { color: C.WHITE }, line: { color: p.color, width: 0.5 }, rectRadius: 0.07 });
    s.addShape("rect", { x, y, w: 0.07, h: 2.55, fill: { color: p.color }, line: { type: "none" } });
    s.addText(p.title, { x: x + 0.18, y: y + 0.12, w: 2.9, h: 0.38, fontFace: "Cambria", fontSize: 12, bold: true, color: p.color, align: "left" });
    s.addText(p.body, { x: x + 0.18, y: y + 0.55, w: 2.9, h: 1.85, fontFace: "Calibri", fontSize: 10, color: C.SLATE, valign: "top", wrap: true });
  });
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 7 â€” RENDERIZAÃ‡ÃƒO POR MALHA
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  s.background = { color: C.LIGHT };
  header(s, "RenderizaÃ§Ã£o por Malha", "Grade de 30 Ã— 30 cÃ©lulas com projeÃ§Ã£o Tsai em lote e fillPoly");
  footerBrand(s, "7");

  bulletCard(s, "DiscretizaÃ§Ã£o em Grade", [
    "900 cÃ©lulas de 5 cm Ã— 5 cm cobrindo 1,5 m Ã— 1,5 m",
    "Altura mÃ©dia por cÃ©lula â€” filtro natural de ruÃ­do do sensor",
    "Pontos fora da mesa descartados antes da acumulaÃ§Ã£o",
    "AcumulaÃ§Ã£o via np.bincount (vetorizado em C â€” ver Slide 8)",
  ], 0.35, 1.42, 5.95, 2.45, { icon: "ðŸ”²" });

  bulletCard(s, "ProjeÃ§Ã£o Tsai em Lote", [
    "961 vÃ©rtices da malha projetados de uma sÃ³ vez via cv2.projectPoints",
    "Cache de vÃ©rtices: sÃ³ recalcula ao recalibrar â€” reutilizado por milhares de frames",
    "Quads (4 vÃ©rtices) montados por fatiamento vetorizado (NumPy)",
  ], 0.35, 4.0, 5.95, 2.4, { icon: "ðŸŽ¯" });

  bulletCard(s, "RasterizaÃ§Ã£o Otimizada", [
    "cv2.fillPoly agrupa polÃ­gonos por cor â€” mÃ¡ximo 3 chamadas por frame",
    "Resultado: grade contÃ­nua sem buracos (vs. projeÃ§Ã£o ponto a ponto ruidosa)",
    "Cobertura 100% â€” cada cÃ©lula Ã© um polÃ­gono preenchido",
  ], 6.55, 1.42, 6.43, 2.45, { icon: "ðŸŽ¨" });

  // diagrama grade visual
  const gx = 6.6, gy = 4.05, gw = 6.3, gh = 2.35;
  s.addShape("rect", { x: gx, y: gy, w: gw, h: gh, fill: { color: C.WHITE }, line: { color: C.STEEL, width: 0.5 }, rectRadius: 0.06 });
  s.addText("VisualizaÃ§Ã£o da Grade de Cores na Areia", { x: gx, y: gy + 0.08, w: gw, h: 0.3, fontFace: "Calibri", fontSize: 10, italic: true, color: C.STEEL, align: "center" });
  // mini grade colorida
  const colors = [[C.ALERT,"C8D0DA"],[C.SUCCESS, C.ALERT],["1565C0", C.SUCCESS]];
  const cellW = 1.2, cellH = 0.56;
  colors.forEach((row, ri) => row.forEach((col, ci) => {
    s.addShape("rect", { x: gx + 1.8 + ci * cellW, y: gy + 0.5 + ri * cellH, w: cellW, h: cellH, fill: { color: col }, line: { color: C.WHITE, width: 0.5 } });
  }));
  s.addText("Vermelho = cavar  Â·  Verde = OK  Â·  Azul = preencher", { x: gx + 0.1, y: gy + 1.9, w: gw - 0.2, h: 0.3, fontFace: "Calibri", fontSize: 9.5, color: C.SLATE, align: "center" });
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 8 â€” GRANULARIDADE E DESEMPENHO
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  s.background = { color: C.LIGHT };
  header(s, "Granularidade e Desempenho", "De 45,5 ms/frame para 17,7 ms/frame â€” ganho de 2,57Ã— sem GPU");
  footerBrand(s, "8");

  // destaque numÃ©rico
  s.addShape("rect", { x: 0.35, y: 1.4, w: 4.2, h: 2.6, fill: { color: C.NAVY }, line: { type: "none" }, rectRadius: 0.1 });
  s.addText("2,57Ã—", { x: 0.35, y: 1.55, w: 4.2, h: 1.3, fontFace: "Cambria", fontSize: 52, bold: true, color: C.GOLD, align: "center", valign: "middle" });
  s.addText("mais rÃ¡pido", { x: 0.35, y: 2.75, w: 4.2, h: 0.38, fontFace: "Calibri", fontSize: 15, color: C.WHITE, align: "center" });
  s.addText("45,5 ms â†’ 17,7 ms / frame", { x: 0.35, y: 3.12, w: 4.2, h: 0.35, fontFace: "Calibri", fontSize: 11, italic: true, color: C.STEEL, align: "center" });
  s.addText("~22 FPS â†’ ~56 FPS (teÃ³rico)", { x: 0.35, y: 3.47, w: 4.2, h: 0.35, fontFace: "Calibri", fontSize: 10.5, color: C.GOLD, align: "center" });

  // tabela antes/depois
  const tabelaX = 4.7, tabelaY = 1.42;
  const rows = [
    { gargalo: "~900 chamadas de desenho/frame", solucao: "Agrupamento por cor â†’ mÃ¡x. 3 chamadas/frame", gain: "â†‘ ~300Ã—" },
    { gargalo: "ProjeÃ§Ã£o geomÃ©trica recalculada a cada frame", solucao: "Cache indexado pela calibraÃ§Ã£o ativa", gain: "â†‘ âˆž" },
    { gargalo: "AcumulaÃ§Ã£o com np.add.at (nÃ£o bufferizado)", solucao: "np.bincount â€” rotina vetorizada em C", gain: "â†‘ 4-8Ã—" },
    { gargalo: "GeoTIFF carregado inteiro (~100 MB)", solucao: "Decimated read â€” leitura reduzida na origem", gain: "â†‘ RAM" },
    { gargalo: "AlocaÃ§Ãµes redundantes por frame", solucao: "Cache Ã­ndices pixel Â· ROI do HUD restrito", gain: "â†‘ CPU" },
  ];

  // header da tabela
  s.addShape("rect", { x: tabelaX, y: tabelaY, w: 8.28, h: 0.4, fill: { color: C.NAVY }, line: { type: "none" } });
  ["Gargalo Original", "SoluÃ§Ã£o Implementada", "Ganho"].forEach((h, i) => {
    const ws = [3.55, 3.95, 0.78];
    const xs = [tabelaX + 0.1, tabelaX + 3.65, tabelaX + 7.6];
    s.addText(h, { x: xs[i], y: tabelaY, w: ws[i], h: 0.4, fontFace: "Cambria", fontSize: 10.5, bold: true, color: C.GOLD, align: "left", valign: "middle" });
  });

  rows.forEach((row, ri) => {
    const ry = tabelaY + 0.42 + ri * 0.68;
    const bg = ri % 2 === 0 ? C.WHITE : C.LIGHT;
    s.addShape("rect", { x: tabelaX, y: ry, w: 8.28, h: 0.66, fill: { color: bg }, line: { color: C.STEEL, width: 0.3 } });
    s.addText(row.gargalo, { x: tabelaX + 0.1, y: ry + 0.04, w: 3.45, h: 0.58, fontFace: "Calibri", fontSize: 9.5, color: C.ALERT, valign: "middle", wrap: true });
    s.addText(row.solucao, { x: tabelaX + 3.65, y: ry + 0.04, w: 3.85, h: 0.58, fontFace: "Calibri", fontSize: 9.5, color: C.SUCCESS, valign: "middle", wrap: true });
    s.addText(row.gain, { x: tabelaX + 7.6, y: ry + 0.04, w: 0.78, h: 0.58, fontFace: "Calibri", fontSize: 10, bold: true, color: C.NAVY, align: "center", valign: "middle" });
  });

  s.addText("MediÃ§Ã£o com nuvem sintÃ©tica de 200.000 pontos Â· grade 30 Ã— 30 Â· sem GPU Â· CPU Intel i5 de geraÃ§Ã£o anterior", {
    x: 4.7, y: 5.85, w: 8.28, h: 0.3, fontFace: "Calibri", fontSize: 9, italic: true, color: C.STEEL, align: "left",
  });
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 9 â€” EMULADOR INTERATIVO (PÃ VIRTUAL)
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  s.background = { color: C.LIGHT };
  header(s, "Emulador Interativo â€” PÃ¡ Virtual", "Modo SimulaÃ§Ã£o: demonstraÃ§Ã£o completa sem sensor fÃ­sico");
  footerBrand(s, "9");

  bulletCard(s, "Cadeia de Fallback (Zero Crash)", [
    "PyKinect2 â€” Kinect v2 via SDK oficial Microsoft",
    "Open3D â€” Azure Kinect / Intel RealSense",
    "libfreenect â€” Kinect v1",
    "Modo SimulaÃ§Ã£o â€” pÃ¡ virtual via mouse (sempre disponÃ­vel)",
  ], 0.35, 1.42, 6.0, 2.75, { icon: "ðŸ“¡", accent: C.NAVY });

  bulletCard(s, "PÃ¡ Virtual (Mouse Callback)", [
    "BotÃ£o esquerdo: CAVAR areia (diminui Z com decaimento Gaussiano)",
    "BotÃ£o direito: PREENCHER areia (aumenta Z)",
    "ParÃ¢metros ajustÃ¡veis: raio (padrÃ£o 5 cm) e intensidade na GUI",
    "Efeito acumulativo proporcional ao tempo de arraste",
  ], 0.35, 4.3, 6.0, 2.6, { icon: "ðŸ–±", accent: C.STEEL });

  bulletCard(s, "Fluxo em Modo SimulaÃ§Ã£o", [
    "Sistema inicializa sem sensor: Z_mesa âˆˆ [-0,20, 0,0] m sintÃ©tico",
    "CalibraÃ§Ã£o automÃ¡tica: T = Identidade (jÃ¡ em coord. da mesa)",
    "Grade 30Ã—30 atualizada em tempo real ao arrastar o mouse",
    "Janelas duplas: Projecao_Areia (limpa) + Gabarito_MDE (HUD)",
  ], 6.6, 1.42, 6.38, 2.75, { icon: "ðŸ’»", accent: C.INFO });

  bulletCard(s, "Teclas de OperaÃ§Ã£o", [
    "[C] â€” Calibrar com tampa plana (RANSAC + SVD)",
    "[M] â€” Alternar mapa: Cubo Central â†” Morro Gaussiano",
    "[F] â€” Tela cheia (janela de projeÃ§Ã£o)",
    "[Q] / ESC â€” Encerrar",
  ], 6.6, 4.3, 6.38, 2.6, { icon: "âŒ¨", accent: C.GOLD });
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 10 â€” RESILIÃŠNCIA E FALLBACK
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  s.background = { color: C.LIGHT };
  header(s, "ResiliÃªncia e Fallback", "\"Zero Crash\" â€” o sistema nunca encerra abruptamente por ausÃªncia de hardware ou arquivo");
  footerBrand(s, "10");

  const cenarios = [
    { title: "Sensor Ausente / IndisponÃ­vel", body: "Entra automaticamente em Modo SimulaÃ§Ã£o\nPÃ¡ virtual via mouse permanece funcional\nDemonstraÃ§Ã£o continua sem interrupÃ§Ã£o", icon: "ðŸ“¡", ok: true },
    { title: "GeoTIFF nÃ£o encontrado / corrompido", body: "Fallback automÃ¡tico para mapa sintÃ©tico\nCubo Central ou Morro Gaussiano gerado\ndinÃ¢micamente â€” [M] alterna em tempo real", icon: "ðŸ—º", ok: true },
    { title: "Falha na CalibraÃ§Ã£o (RANSAC)", body: "RuntimeError capturado â€” volta para IDLE\nMensagem de erro no console\nTecla [C] disponÃ­vel para nova tentativa", icon: "ðŸ“", ok: true },
    { title: "CalibraÃ§Ã£o JSON corrompida", body: "carregar_matriz_calibracao() retorna None\nFluxo redireciona para calibraÃ§Ã£o manual\nSem exceÃ§Ã£o propagada ao usuÃ¡rio", icon: "ðŸ’¾", ok: true },
    { title: "Open3D nÃ£o instalado", body: "Teste de importaÃ§Ã£o ignorado (skipTest)\n58 de 59 testes passam normalmente\nFuncionalidade alternativa disponÃ­vel", icon: "âš™", ok: true },
    { title: "Console Windows cp1252", body: "stdout/stderr reconfigurados para UTF-8\nSÃ­mbolos matemÃ¡ticos (âˆˆ, â†’, Ã—) impressos\nsem UnicodeEncodeError na apresentaÃ§Ã£o", icon: "ðŸ–¥", ok: true },
  ];

  cenarios.forEach((c, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = 0.35 + col * 4.34, y = 1.42 + row * 2.72;
    s.addShape("rect", { x: x + 0.04, y: y + 0.04, w: 4.1, h: 2.5, fill: { color: C.SHADOW || "C8D0DA" }, line: { type: "none" }, rectRadius: 0.07 });
    s.addShape("rect", { x, y, w: 4.1, h: 2.5, fill: { color: C.WHITE }, line: { color: C.SUCCESS, width: 0.5 }, rectRadius: 0.07 });
    s.addShape("rect", { x, y, w: 0.07, h: 2.5, fill: { color: C.SUCCESS }, line: { type: "none" } });
    s.addText(c.icon, { x: x + 0.18, y: y + 0.1, w: 0.5, h: 0.48, fontFace: "Calibri", fontSize: 20, align: "left" });
    s.addText("âœ“ Tratado", { x: x + 3.4, y: y + 0.15, w: 0.65, h: 0.3, fontFace: "Calibri", fontSize: 8.5, bold: true, color: C.SUCCESS, align: "right" });
    s.addText(c.title, { x: x + 0.18, y: y + 0.62, w: 3.78, h: 0.4, fontFace: "Cambria", fontSize: 11, bold: true, color: C.NAVY, align: "left" });
    s.addText(c.body, { x: x + 0.18, y: y + 1.05, w: 3.78, h: 1.35, fontFace: "Calibri", fontSize: 10, color: C.SLATE, valign: "top", wrap: true });
  });
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 11 â€” REGRA DE NEGÃ“CIO (LÃ“GICA DE CORES)
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  s.background = { color: C.LIGHT };
  header(s, "Regra de NegÃ³cio â€” LÃ³gica de Cores", "ComparaÃ§Ã£o Z_real vs Z_alvo(MDE) com tolerÃ¢ncia Ï„ = Â±2 cm");
  footerBrand(s, "11");

  // fÃ³rmula central
  s.addShape("rect", { x: 0.35, y: 1.42, w: 12.63, h: 0.85, fill: { color: C.NAVY }, line: { type: "none" }, rectRadius: 0.08 });
  s.addText("ClassificaÃ§Ã£o: diff = Z_real âˆ’ Z_alvo(x, y)", { x: 0.45, y: 1.42, w: 12.43, h: 0.4, fontFace: "Cambria", fontSize: 14, bold: true, color: C.GOLD, align: "center", valign: "bottom" });
  s.addText("diff > +Ï„  â†’  VERMELHO (cavar)     |     diff < âˆ’Ï„  â†’  AZUL (preencher)     |     |diff| â‰¤ Ï„  â†’  VERDE (OK)", {
    x: 0.45, y: 1.78, w: 12.43, h: 0.38, fontFace: "Calibri", fontSize: 12, color: C.WHITE, align: "center", valign: "middle",
  });

  // trÃªs cards de cor
  const colors = [
    { title: "VERMELHO â€” Cavar", body: "Z_real > Z_alvo + Ï„\nAreia em excesso\nOperador deve remover areia\nExemplo: platÃ´ alvo âˆ’10 cm,\nareia atual em âˆ’5 cm", color: C.ALERT, bgr: "(0, 0, 255)" },
    { title: "VERDE â€” Conforme", body: "|Z_real âˆ’ Z_alvo| â‰¤ Ï„\nAltura dentro da tolerÃ¢ncia\nÂ±2 cm = Â±20 mm\nSinal de aprovaÃ§Ã£o:\nnÃ£o hÃ¡ aÃ§Ã£o necessÃ¡ria", color: C.SUCCESS, bgr: "(0, 255, 0)" },
    { title: "AZUL â€” Preencher", body: "Z_real < Z_alvo âˆ’ Ï„\nAreia insuficiente\nOperador deve adicionar areia\nExemplo: platÃ´ alvo âˆ’10 cm,\nareia atual em âˆ’15 cm", color: C.INFO, bgr: "(255, 0, 0)" },
  ];

  colors.forEach((c, i) => {
    const x = 0.35 + i * 4.34;
    s.addShape("rect", { x: x + 0.04, y: 2.42, w: 4.1, h: 3.35, fill: { color: C.SHADOW || "C8D0DA" }, line: { type: "none" }, rectRadius: 0.08 });
    s.addShape("rect", { x, y: 2.42, w: 4.1, h: 3.35, fill: { color: c.color }, line: { type: "none" }, rectRadius: 0.08 });
    s.addText(c.title, { x: x + 0.12, y: 2.55, w: 3.86, h: 0.5, fontFace: "Cambria", fontSize: 14, bold: true, color: C.WHITE, align: "center" });
    hRule(s, x + 0.2, 3.1, 3.7, C.WHITE, 1);
    s.addText(c.body, { x: x + 0.12, y: 3.18, w: 3.86, h: 1.85, fontFace: "Calibri", fontSize: 11, color: C.WHITE, align: "center", valign: "top", wrap: true });
    s.addText(`BGR: ${c.bgr}`, { x: x + 0.12, y: 5.25, w: 3.86, h: 0.35, fontFace: "Calibri", fontSize: 9.5, italic: true, color: C.WHITE, align: "center" });
  });

  s.addText("ImplementaÃ§Ã£o vetorizada: cor_por_diferenca_vetorizado() â€” classifica 900 cÃ©lulas em uma Ãºnica operaÃ§Ã£o NumPy por frame", {
    x: 0.35, y: 5.88, w: 12.63, h: 0.3, fontFace: "Calibri", fontSize: 9.5, italic: true, color: C.STEEL, align: "center",
  });
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 12 â€” QUALIDADE E TDD
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  s.background = { color: C.LIGHT };
  header(s, "Qualidade e TDD â€” Testes Automatizados", "59 testes unitÃ¡rios Â· 58 aprovados Â· 1 ignorado (Open3D opcional)");
  footerBrand(s, "12");

  // destaque numÃ©rico
  s.addShape("rect", { x: 0.35, y: 1.42, w: 3.5, h: 4.85, fill: { color: C.NAVY }, line: { type: "none" }, rectRadius: 0.1 });
  s.addText("59", { x: 0.35, y: 1.6, w: 3.5, h: 1.6, fontFace: "Cambria", fontSize: 68, bold: true, color: C.GOLD, align: "center" });
  s.addText("testes automatizados", { x: 0.35, y: 3.15, w: 3.5, h: 0.4, fontFace: "Calibri", fontSize: 12, color: C.WHITE, align: "center" });
  s.addShape("rect", { x: 0.55, y: 3.65, w: 3.1, h: 0.38, fill: { color: C.SUCCESS }, line: { type: "none" }, rectRadius: 0.06 });
  s.addText("58 APROVADOS", { x: 0.55, y: 3.65, w: 3.1, h: 0.38, fontFace: "Calibri", fontSize: 12, bold: true, color: C.WHITE, align: "center", valign: "middle" });
  s.addShape("rect", { x: 0.55, y: 4.13, w: 3.1, h: 0.38, fill: { color: C.STEEL }, line: { type: "none" }, rectRadius: 0.06 });
  s.addText("1 IGNORADO (Open3D)", { x: 0.55, y: 4.13, w: 3.1, h: 0.38, fontFace: "Calibri", fontSize: 11, bold: true, color: C.WHITE, align: "center", valign: "middle" });
  s.addText("python -m pytest\ntest_motor_caixao.py -v", { x: 0.35, y: 4.65, w: 3.5, h: 0.85, fontFace: "Calibri", fontSize: 9.5, italic: true, color: C.GOLD, align: "center" });

  // suite de classes
  const suites = [
    { title: "TestAjustePlano (4)", body: "Plano horizontal, inclinado, normal unitÃ¡ria, pontos insuficientes" },
    { title: "TestRANSAC (5)", body: "Outliers de moldura/piso, limiar 3 cm, refinamento SVD sobre inliers" },
    { title: "TestGramSchmidt + Base (5)", body: "Ortogonalidade, valore paralelos, base ortonormal" },
    { title: "TestMatrizTransformacao (3)", body: "Identidade, translaÃ§Ã£o, ponto no plano â†’ Z=0" },
    { title: "TestDeteccaoTabuleiro (2)", body: "Imagem branca (sem cantos) e tabuleiro sintÃ©tico 7Ã—5" },
    { title: "TestProjecaoTsai (3)", body: "Ponto principal, deslocamento X, mÃºltiplos pontos" },
    { title: "TestBackProjectionMesa (4)", body: "Pixel central, deslocado, fora do alcance, sinal Z_mesa" },
    { title: "TestCalibracaoTampa (6)", body: "Normal vertical, Z=0, T_shift, areia negativa, RANSAC+moldura" },
    { title: "TestPipeline + PersistÃªncia (6)", body: "Pipeline integrado, cache JSON round-trip, JSON corrompido" },
    { title: "TestCuboCentral (7)", body: "PlatÃ´ âˆ’10 cm, fundo âˆ’20 cm, bordas, vetorizado, AdaptadorMDE" },
    { title: "TestColoracaoBGR + Grade (13)", body: "Todas as combinaÃ§Ãµes de cor + renderizaÃ§Ã£o ponta a ponta" },
  ];

  suites.forEach((suite, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 4.05 + col * 4.72, y = 1.42 + row * 0.88;
    s.addShape("rect", { x, y, w: 4.5, h: 0.8, fill: { color: i % 2 === 0 ? C.WHITE : "F8F9FA" }, line: { color: C.STEEL, width: 0.3 }, rectRadius: 0.05 });
    s.addShape("rect", { x, y, w: 0.06, h: 0.8, fill: { color: C.SUCCESS }, line: { type: "none" } });
    s.addText(suite.title, { x: x + 0.15, y: y + 0.05, w: 4.28, h: 0.3, fontFace: "Cambria", fontSize: 10.5, bold: true, color: C.NAVY, align: "left" });
    s.addText(suite.body, { x: x + 0.15, y: y + 0.36, w: 4.28, h: 0.38, fontFace: "Calibri", fontSize: 9, color: C.SLATE, align: "left", valign: "top", wrap: true });
  });
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 13 â€” GUIA DE EXECUÃ‡ÃƒO
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  s.background = { color: C.LIGHT };
  header(s, "Guia de ExecuÃ§Ã£o â€” InstalaÃ§Ã£o Simplificada", "TrÃªs comandos para instalar Â· operaÃ§Ã£o offline Â· instalÃ¡vel por pessoal sem formaÃ§Ã£o tÃ©cnica");
  footerBrand(s, "13");

  // comandos
  const cmds = [
    { n: "1", label: "Criar ambiente virtual isolado", cmd: "python -m venv kinect_env", desc: "Isola as dependÃªncias do projeto â€” nÃ£o interfere com outras instalaÃ§Ãµes Python" },
    { n: "2", label: "Ativar o ambiente", cmd: ".\\kinect_env\\Scripts\\Activate.ps1", desc: "Ativa o ambiente isolado (PowerShell). Prompt muda para (kinect_env)" },
    { n: "3", label: "Instalar dependÃªncias", cmd: "pip install -r requirements.txt", desc: "Instala automaticamente todas as bibliotecas (numpy, opencv, customtkinterâ€¦)" },
    { n: "4", label: "Executar o sistema", cmd: "python main.py", desc: "Abre a GUI de configuraÃ§Ã£o. Selecionar mapa ou modo demonstraÃ§Ã£o e iniciar" },
  ];

  cmds.forEach((cmd, i) => {
    const y = 1.42 + i * 1.35;
    // nÃºmero
    s.addShape("ellipse", { x: 0.35, y: y + 0.35, w: 0.55, h: 0.55, fill: { color: C.NAVY }, line: { type: "none" } });
    s.addText(cmd.n, { x: 0.35, y: y + 0.35, w: 0.55, h: 0.55, fontFace: "Cambria", fontSize: 16, bold: true, color: C.GOLD, align: "center", valign: "middle" });
    // card
    s.addShape("rect", { x: 1.05, y, w: 11.93, h: 1.25, fill: { color: C.WHITE }, line: { color: C.STEEL, width: 0.5 }, rectRadius: 0.07 });
    s.addShape("rect", { x: 1.05, y, w: 0.07, h: 1.25, fill: { color: C.GOLD }, line: { type: "none" } });
    // label
    s.addText(cmd.label, { x: 1.22, y: y + 0.08, w: 11.65, h: 0.3, fontFace: "Cambria", fontSize: 11.5, bold: true, color: C.NAVY, align: "left" });
    // comando
    s.addShape("rect", { x: 1.22, y: y + 0.4, w: 8.0, h: 0.38, fill: { color: C.NAVY }, line: { type: "none" }, rectRadius: 0.04 });
    s.addText(cmd.cmd, { x: 1.3, y: y + 0.4, w: 7.84, h: 0.38, fontFace: "Courier New", fontSize: 11, color: C.GOLD, align: "left", valign: "middle" });
    // descriÃ§Ã£o
    s.addText(cmd.desc, { x: 1.22, y: y + 0.85, w: 11.65, h: 0.3, fontFace: "Calibri", fontSize: 9.5, color: C.SLATE, align: "left" });
  });

  s.addText("ApÃ³s instalaÃ§Ã£o: 100% offline Â· sem dependÃªncia de internet Â· operÃ¡vel por instrutor sem formaÃ§Ã£o em TI", {
    x: 0.35, y: 6.9, w: 12.63, h: 0.3, fontFace: "Calibri", fontSize: 10, italic: true, color: C.STEEL, align: "center",
  });
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 14 â€” INTERFACE DO USUÃRIO (GUI)
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  s.background = { color: C.LIGHT };
  header(s, "Interface do UsuÃ¡rio â€” CustomTkinter GUI", "Janela de configuraÃ§Ã£o com validaÃ§Ã£o em tempo real Â· dark/light automÃ¡tico Â· perfis JSON");
  footerBrand(s, "14");

  bulletCard(s, "GUI de ConfiguraÃ§Ã£o Inicial (CustomTkinter)", [
    "Layout em abas: Mapa TÃ¡tico Â· DimensÃµes FÃ­sicas Â· SimulaÃ§Ã£o AvanÃ§ada",
    "ValidaÃ§Ã£o em tempo real: borda vermelha + mensagem enquanto hÃ¡ erro",
    "BotÃ£o INICIAR habilitado apenas com todos os campos vÃ¡lidos",
    "Salvar / Carregar ConfiguraÃ§Ã£o como perfil .json (uso recorrente)",
    "Troca de tema dark/light pelo SegmentedButton (Claro / Escuro / Sistema)",
  ], 0.35, 1.42, 6.0, 3.1, { icon: "ðŸ–¥" });

  bulletCard(s, "ParÃ¢metros ConfigurÃ¡veis", [
    "Mesa: largura Ã— comprimento Ã— profundidade (m)",
    "Kinect: altura de montagem (m)",
    "TolerÃ¢ncia de cor: Ï„ em metros",
    "ResoluÃ§Ã£o do projetor (px)",
    "Malha: cÃ©lulas em X e Y",
    "RANSAC: iteraÃ§Ãµes e limiar de inlier (m)",
    "PÃ¡ Virtual: raio e intensidade",
    "ForÃ§ar Modo SimulaÃ§Ã£o: ignora Kinect conectado",
  ], 0.35, 4.65, 6.0, 2.65, { icon: "âš™" });

  bulletCard(s, "Janelas em Tempo de ExecuÃ§Ã£o", [
    "Projecao_Areia â€” grade AR pura (vermelho/azul/verde)\nâ†’ sem HUD, projetada sobre a areia fÃ­sica",
    "Gabarito_MDE â€” heatmap de referÃªncia do MDE\n+ legenda de cores + HUD de estado + FPS\nâ†’ janela do operador, nunca projetada",
  ], 6.6, 1.42, 6.38, 2.65, { icon: "ðŸªŸ" });

  bulletCard(s, "Mapas de ReferÃªncia", [
    "GeoTIFF real: terreno cartogrÃ¡fico da AMAN\n(rasterio + scipy.interpolate)",
    "Cubo Central: platÃ´ quadrado âˆ’10 cm\n(fallback padrÃ£o â€” sempre disponÃ­vel)",
    "Morro Gaussiano: monte suave centralizado\n(alternÃ¡vel com tecla [M])",
  ], 6.6, 4.2, 6.38, 3.1, { icon: "ðŸ—º" });
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 15 â€” DIVISOR PARTE 2: ENG. ELETRÃ”NICA
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  sectionDivider(s, "PARTE 2", "Engenharia EletrÃ´nica", "Hardware Â· Kinect Â· ProjeÃ§Ã£o Â· CaixÃ£o de Areia");
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 16 â€” HARDWARE DO SISTEMA
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  s.background = { color: C.LIGHT };
  header(s, "Hardware do Sistema", "Componentes fÃ­sicos: sensor de profundidade, projetor e estrutura");
  footerBrand(s, "16");

  const hw = [
    { title: "Microsoft Kinect v2", sub: "Sensor Principal", body: "ResoluÃ§Ã£o de profundidade: 512Ã—424 px\nResoluÃ§Ã£o de cor: 1920Ã—1080 px\nAlcance: 0,5 m a 4,5 m\nFOV: 70Â° (H) Ã— 60Â° (V)\nMontado a 2,5 m de altura", icon: "ðŸ“¡", color: C.NAVY },
    { title: "Projetor DLP / LCD", sub: "SaÃ­da Visual", body: "ResoluÃ§Ã£o mÃ­nima: 640Ã—480 px (SVGA)\nOperaÃ§Ã£o: apontado para baixo ou\nvia espelho refletor (ver prÃ³x. slide)\nSaÃ­da: grade colorida sobre areia", icon: "ðŸ“½", color: C.INFO },
    { title: "Computador de Controle", sub: "Processamento", body: "CPU: qualquer Intel i5+ (sem GPU)\nRAM: 8 GB recomendado\nSO: Windows 10/11 (PowerShell)\nSem necessidade de placa de vÃ­deo\ndedicada â€” requisito de projeto", icon: "ðŸ’»", color: C.STEEL },
  ];

  hw.forEach((h, i) => {
    const x = 0.35 + i * 4.34, y = 1.42;
    s.addShape("rect", { x: x + 0.04, y: y + 0.04, w: 4.1, h: 4.15, fill: { color: C.SHADOW || "C8D0DA" }, line: { type: "none" }, rectRadius: 0.08 });
    s.addShape("rect", { x, y, w: 4.1, h: 4.15, fill: { color: C.WHITE }, line: { color: h.color, width: 1 }, rectRadius: 0.08 });
    s.addShape("rect", { x, y, w: 4.1, h: 0.07, fill: { color: h.color }, line: { type: "none" }, rectRadius: 0.04 });
    s.addText(h.icon, { x, y: y + 0.18, w: 4.1, h: 0.7, fontFace: "Calibri", fontSize: 28, align: "center" });
    s.addText(h.title, { x: x + 0.12, y: y + 0.95, w: 3.86, h: 0.42, fontFace: "Cambria", fontSize: 13, bold: true, color: h.color, align: "center" });
    s.addText(h.sub, { x: x + 0.12, y: y + 1.35, w: 3.86, h: 0.28, fontFace: "Calibri", fontSize: 10.5, italic: true, color: C.STEEL, align: "center" });
    hRule(s, x + 0.3, y + 1.65, 3.5, h.color, 1);
    s.addText(h.body, { x: x + 0.2, y: y + 1.78, w: 3.7, h: 2.25, fontFace: "Calibri", fontSize: 10.5, color: C.SLATE, valign: "top", wrap: true });
  });

  s.addShape("rect", { x: 0.35, y: 5.72, w: 12.63, h: 0.6, fill: { color: C.NAVY }, line: { type: "none" }, rectRadius: 0.07 });
  s.addText("DimensÃµes fÃ­sicas da mesa: 1,5 m Ã— 1,5 m Ã— 0,20 m de profundidade  Â·  Grade de discretizaÃ§Ã£o: 30 Ã— 30 cÃ©lulas de 5 cm Ã— 5 cm", {
    x: 0.45, y: 5.72, w: 12.43, h: 0.6, fontFace: "Calibri", fontSize: 11, color: C.GOLD, align: "center", valign: "middle",
  });
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 17 â€” ADAPTAÃ‡ÃƒO DO KINECT
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  s.background = { color: C.LIGHT };
  header(s, "AdaptaÃ§Ã£o do Kinect", "CalibraÃ§Ã£o de tampa, parÃ¢metros intrÃ­nsecos e integraÃ§Ã£o com o motor matemÃ¡tico");
  footerBrand(s, "17");

  bulletCard(s, "ParÃ¢metros IntrÃ­nsecos (Kinect v2)", [
    "fx = fy â‰ˆ 525 px (focal em pixels)",
    "cx â‰ˆ 319,5 px, cy â‰ˆ 239,5 px (ponto principal)",
    "ResoluÃ§Ã£o: 512 Ã— 424 px (profundidade)",
    "Faixa vÃ¡lida: 0,3 m a 4,5 m",
    "Mapa de profundidade: uint16 em milÃ­metros",
  ], 0.35, 1.42, 6.0, 2.85, { icon: "ðŸ“" });

  bulletCard(s, "LimitaÃ§Ãµes Conhecidas do Kinect", [
    "FOV mais largo que o caixÃ£o â†’ captura moldura e piso (â†’ RANSAC)",
    "RuÃ­do de profundidade Â±1-2 cm â†’ filtrado pela mÃ©dia por cÃ©lula da grade",
    "Descontinuidade na borda de objetos (efeito \"flying pixels\")",
    "Luz solar direta interfere na leitura de IR",
  ], 0.35, 4.42, 6.0, 2.88, { icon: "âš " , accent: C.STEEL });

  bulletCard(s, "CalibraÃ§Ã£o da Tampa (Lid Calibration)", [
    "Tampa lisa e plana cobre toda a Ã¡rea do caixÃ£o",
    "Representa Z_mesa = 0,0 m (nÃ­vel mÃ¡ximo de areia)",
    "Com a tampa: RANSAC â†’ SVD â†’ Gram-Schmidt â†’ T_final (4Ã—4)",
    "T_final salvo em calibration_data.json â€” reutilizado nas prÃ³ximas execuÃ§Ãµes",
    "NecessÃ¡rio recalibrar sÃ³ ao reposicionar fisicamente o sensor",
  ], 6.6, 1.42, 6.38, 2.85, { icon: "ðŸ”§" });

  bulletCard(s, "Modo SimulaÃ§Ã£o (sem Kinect)", [
    "KinectSensor.esta_simulando = True",
    "Areia sintÃ©tica em array 2D (numpy) â€” grades 30Ã—30",
    "Z_mesa âˆˆ [âˆ’0,20, 0,0] m mantido por clamp automÃ¡tico",
    "IntegraÃ§Ã£o com pÃ¡ virtual via callback de mouse",
    "Mesmo pipeline matemÃ¡tico do modo real",
  ], 6.6, 4.42, 6.38, 2.88, { icon: "ðŸ’»" });
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 18 â€” SOLUÃ‡ÃƒO DE PROJEÃ‡ÃƒO: ESPELHO REFLETOR  â˜… NOVO
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  s.background = { color: C.LIGHT };
  // badge NOVO
  s.addShape("rect", { x: 10.5, y: 0.18, w: 1.1, h: 0.32, fill: { color: C.GOLD }, line: { type: "none" }, rectRadius: 0.05 });
  s.addText("â˜… NOVO", { x: 10.5, y: 0.18, w: 1.1, h: 0.32, fontFace: "Calibri", fontSize: 9, bold: true, color: C.NAVY, align: "center", valign: "middle" });
  header(s, "SoluÃ§Ã£o de ProjeÃ§Ã£o: Espelho Refletor", "ProjeÃ§Ã£o indireta via espelho plano â€” soluÃ§Ã£o provisÃ³ria validada no caixÃ£o antigo");
  footerBrand(s, "18");

  // DIAGRAMA Ã“PTICO (shapes nativos)
  const dx = 0.4, dy = 1.42;

  // Projetor (retÃ¢ngulo)
  s.addShape("rect", { x: dx, y: dy + 0.4, w: 1.55, h: 0.75, fill: { color: C.NAVY }, line: { type: "none" }, rectRadius: 0.06 });
  s.addText("ðŸ“½ Projetor", { x: dx, y: dy + 0.4, w: 1.55, h: 0.75, fontFace: "Calibri", fontSize: 11, bold: true, color: C.WHITE, align: "center", valign: "middle" });

  // seta para espelho
  s.addShape("rightArrow", { x: dx + 1.6, y: dy + 0.65, w: 1.2, h: 0.28, fill: { color: C.GOLD }, line: { type: "none" } });

  // Espelho
  s.addShape("rect", { x: dx + 2.88, y: dy + 0.28, w: 1.35, h: 1.0, fill: { color: C.STEEL }, line: { color: C.NAVY, width: 1 }, rectRadius: 0.05 });
  s.addText("Espelho\nPlano", { x: dx + 2.88, y: dy + 0.28, w: 1.35, h: 1.0, fontFace: "Calibri", fontSize: 11, bold: true, color: C.WHITE, align: "center", valign: "middle" });

  // seta para baixo (reflexÃ£o)
  s.addShape("downArrow", { x: dx + 3.28, y: dy + 1.35, w: 0.55, h: 0.9, fill: { color: C.GOLD }, line: { type: "none" } });

  // Areia
  s.addShape("rect", { x: dx + 2.78, y: dy + 2.32, w: 1.75, h: 0.65, fill: { color: "C8A050" }, line: { type: "none" }, rectRadius: 0.05 });
  s.addText("Areia", { x: dx + 2.78, y: dy + 2.32, w: 1.75, h: 0.65, fontFace: "Calibri", fontSize: 12, bold: true, color: C.WHITE, align: "center", valign: "middle" });

  // labels de caminho Ã³ptico
  s.addText("Feixe luminoso horizontal", { x: dx + 1.62, y: dy + 0.35, w: 1.2, h: 0.28, fontFace: "Calibri", fontSize: 8.5, italic: true, color: C.SLATE, align: "center" });
  s.addText("ReflexÃ£o\nvertical", { x: dx + 3.88, y: dy + 1.58, w: 1.0, h: 0.55, fontFace: "Calibri", fontSize: 8.5, italic: true, color: C.SLATE, align: "left" });

  // Kinect
  s.addShape("rect", { x: dx, y: dy + 1.8, w: 1.3, h: 0.65, fill: { color: C.INFO }, line: { type: "none" }, rectRadius: 0.05 });
  s.addText("ðŸ“¡ Kinect", { x: dx, y: dy + 1.8, w: 1.3, h: 0.65, fontFace: "Calibri", fontSize: 11, bold: true, color: C.WHITE, align: "center", valign: "middle" });
  s.addShape("rightArrow", { x: dx + 1.35, y: dy + 2.02, w: 1.38, h: 0.2, fill: { color: C.INFO }, line: { type: "none" } });
  s.addText("Leitura de profundidade", { x: dx + 1.35, y: dy + 1.78, w: 1.38, h: 0.22, fontFace: "Calibri", fontSize: 7.5, italic: true, color: C.SLATE, align: "center" });

  // retÃ¢ngulo de caixÃ£o
  s.addShape("rect", { x: dx + 2.0, y: dy + 2.05, w: 2.8, h: 1.1, fill: { color: "none" }, line: { color: C.SLATE, width: 1.5, dashType: "dash" }, rectRadius: 0.04 });
  s.addText("CaixÃ£o de Areia (antigo)", { x: dx + 2.0, y: dy + 3.18, w: 2.8, h: 0.25, fontFace: "Calibri", fontSize: 8, italic: true, color: C.SLATE, align: "center" });

  // coluna de bullets
  bulletCard(s, "Por que o espelho?", [
    "Projetor apontado diretamente para baixo exigiria suporte a > 2,5 m de altura",
    "EspaÃ§o fÃ­sico limitado na sala â€” estrutura original do caixÃ£o antigo nÃ£o permite",
    "Espelho plano permite posicionar o projetor lateralmente em altura convencional",
    "Feixe horizontal refletido torna-se vertical sobre a areia",
  ], 5.6, 1.42, 7.38, 2.55, { icon: "ðŸ’¡", accent: C.NAVY });

  bulletCard(s, "Resultado Validado", [
    "IntegraÃ§Ã£o projetor + Kinect funcionando simultaneamente",
    "AtualizaÃ§Ã£o de cores em tempo real: vermelho, azul e verde sobre a areia",
    "Sem interferÃªncia entre o feixe IR do Kinect e a luz do projetor",
    "ConfirmaÃ§Ã£o de viabilidade da soluÃ§Ã£o de projeÃ§Ã£o indireta",
  ], 5.6, 4.1, 7.38, 2.3, { icon: "âœ…", accent: C.SUCCESS });

  // placeholders de foto
  // IMG("espelho_setup.png") â€” foto geral do setup
  photoPlaceholder(s, 5.6, 6.5, 3.55, 0.82, "[FOTO: espelho_setup.png â€” projetor + espelho montados no caixÃ£o antigo]");
  // IMG("espelho_projecao_areia.png") â€” foto de perto com cores
  photoPlaceholder(s, 9.38, 6.5, 3.6, 0.82, "[FOTO: espelho_projecao_areia.png â€” projeÃ§Ã£o colorida refletida na areia]");
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 19 â€” NOVO CAIXÃƒO DE AREIA (MARCENARIA)  â˜… NOVO
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  s.background = { color: C.LIGHT };
  s.addShape("rect", { x: 10.5, y: 0.18, w: 1.1, h: 0.32, fill: { color: C.GOLD }, line: { type: "none" }, rectRadius: 0.05 });
  s.addText("â˜… NOVO", { x: 10.5, y: 0.18, w: 1.1, h: 0.32, fontFace: "Calibri", fontSize: 9, bold: true, color: C.NAVY, align: "center", valign: "middle" });
  header(s, "Novo CaixÃ£o de Areia â€” Marcenaria", "Estrutura definitiva construÃ­da sob medida para a versÃ£o final do hardware");
  footerBrand(s, "19");

  bulletCard(s, "CaixÃ£o Anterior â€” ProtÃ³tipo Funcional", [
    "CaixÃ£o reutilizado de prateleira comercial (protÃ³tipo improvÃ¡vel)",
    "Validou o motor matemÃ¡tico e a integraÃ§Ã£o eletrÃ´nica inicial",
    "LimitaÃ§Ã£o: estrutura nÃ£o permite fixaÃ§Ã£o estÃ¡vel do Kinect e do projetor",
    "SoluÃ§Ã£o provisÃ³ria com espelho confirmou a viabilidade do caminho Ã³ptico",
  ], 0.35, 1.42, 6.2, 2.85, { icon: "ðŸ“¦", accent: C.STEEL });

  bulletCard(s, "Novo CaixÃ£o â€” Marcenaria sob Medida", [
    "ConstruÃ­do com dimensÃµes exatas: 1,5 m Ã— 1,5 m Ã— 0,20 m de profundidade",
    "Suporte integrado para o Kinect a 2,5 m de altura",
    "Suporte para projetor (direto ou via espelho) â€” fixo e estÃ¡vel",
    "Resolve o desafio de \"FixaÃ§Ã£o FÃ­sica\" listado nos Desafios em Aberto",
    "VersÃ£o final do hardware do projeto",
  ], 0.35, 4.42, 6.2, 2.85, { icon: "ðŸªµ", accent: C.GOLD });

  // linha do tempo: protÃ³tipo â†’ espelho â†’ caixÃ£o novo
  const timeY = 1.42;
  [[7.0, "CaixÃ£o Antigo\n(protÃ³tipo)", C.STEEL],
   [9.1, "Espelho +\nProjetor (validaÃ§Ã£o)", C.INFO],
   [11.2, "CaixÃ£o Novo\n(marcenaria)", C.SUCCESS]].forEach(([x, label, color], i) => {
     s.addShape("ellipse", { x, y: timeY + 0.25, w: 0.6, h: 0.6, fill: { color }, line: { type: "none" } });
     s.addText(String(i + 1), { x, y: timeY + 0.25, w: 0.6, h: 0.6, fontFace: "Cambria", fontSize: 16, bold: true, color: C.WHITE, align: "center", valign: "middle" });
     s.addText(label, { x: x - 0.5, y: timeY + 0.92, w: 1.6, h: 0.7, fontFace: "Calibri", fontSize: 9.5, color: color, align: "center", wrap: true });
     if (i < 2) s.addShape("rightArrow", { x: x + 0.65, y: timeY + 0.42, w: 1.38, h: 0.25, fill: { color: C.GOLD }, line: { type: "none" } });
  });

  // placeholders de foto
  photoPlaceholder(s, 6.75, 2.2, 3.1, 2.3, "[FOTO: caixao_novo_vazio.png\nnovo caixÃ£o em marcenaria (vazio)]");
  photoPlaceholder(s, 10.05, 2.2, 3.1, 2.3, "[FOTO: caixao_novo_areia.png\nnovo caixÃ£o com areia]");

  // nota sobre integraÃ§Ã£o futura
  s.addShape("rect", { x: 6.65, y: 4.65, w: 6.48, h: 2.62, fill: { color: C.WHITE }, line: { color: C.SUCCESS, width: 0.5 }, rectRadius: 0.07 });
  s.addShape("rect", { x: 6.65, y: 4.65, w: 0.07, h: 2.62, fill: { color: C.SUCCESS }, line: { type: "none" } });
  s.addText("ðŸŽ¯  PrÃ³ximo Passo", { x: 6.82, y: 4.72, w: 6.2, h: 0.35, fontFace: "Cambria", fontSize: 12, bold: true, color: C.SUCCESS, align: "left" });
  s.addText([
    "Migrar a soluÃ§Ã£o validada (Kinect + espelho + projetor) para o novo caixÃ£o.",
    "Fixar definitivamente o Kinect e o sistema de projeÃ§Ã£o na nova estrutura.",
    "Realizar calibraÃ§Ã£o final com a tampa nas dimensÃµes corretas.",
    "Entrega do produto acabado para a SeÃ§Ã£o de SimulaÃ§Ã£o da AMAN.",
  ].join("\n"), { x: 6.82, y: 5.12, w: 6.2, h: 2.1, fontFace: "Calibri", fontSize: 10.5, color: C.SLATE, valign: "top", wrap: true });
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 20 â€” DIVISOR PARTE 3: RESULTADOS
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  sectionDivider(s, "PARTE 3", "Resultados e PrÃ³ximos Passos", "Estado Atual Â· Desafios em Aberto Â· Roadmap Â· Cronograma");
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 21 â€” ESTADO ATUAL DO SISTEMA
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  s.background = { color: C.LIGHT };
  header(s, "Estado Atual do Sistema", "VerificaÃ§Ã£o de Curso (VC) â€” Julho 2026");
  footerBrand(s, "21");

  const items = [
    { area: "Motor MatemÃ¡tico (Python)", status: "Completo", detail: "RANSAC Â· SVD Â· Gram-Schmidt Â· Tsai Â· Grade 30Ã—30", color: C.SUCCESS },
    { area: "OtimizaÃ§Ã£o de Desempenho", status: "Completo", detail: "2,57Ã— mais rÃ¡pido Â· sem GPU Â· 17,7 ms/frame", color: C.SUCCESS },
    { area: "SuÃ­te de Testes (TDD)", status: "Completo", detail: "59 testes â€” 58 aprovados Â· 1 ignorado (Open3D)", color: C.SUCCESS },
    { area: "Interface GrÃ¡fica (GUI)", status: "Completo", detail: "CustomTkinter Â· abas Â· validaÃ§Ã£o em tempo real Â· perfis JSON", color: C.SUCCESS },
    { area: "Emulador / PÃ¡ Virtual", status: "Completo", detail: "Modo simulaÃ§Ã£o interativo â€” demonstrÃ¡vel sem hardware", color: C.SUCCESS },
    { area: "DocumentaÃ§Ã£o", status: "Completo", detail: "DOCUMENTACAO_OFICIAL.md Â· GUIA_INSTALACAO_INICIANTES.md", color: C.SUCCESS },
    { area: "AdaptaÃ§Ã£o do Kinect", status: "Completo", detail: "CalibraÃ§Ã£o tampa Â· RANSAC Â· cache JSON Â· fallback em cascata", color: C.SUCCESS },
    { area: "IntegraÃ§Ã£o Projetor/Estrutura", status: "Funcional â€” soluÃ§Ã£o provisÃ³ria", detail: "Validado via espelho refletor no caixÃ£o antigo Â· cores em tempo real (V/A/V)", color: C.GOLD },
    { area: "CaixÃ£o Definitivo (Marcenaria)", status: "ConcluÃ­do", detail: "Novo caixÃ£o construÃ­do sob medida â€” pronto para integraÃ§Ã£o final", color: C.SUCCESS },
    { area: "MDE Real (GeoTIFF AMAN)", status: "Pendente (VF)", detail: "Arquivo cartogrÃ¡fico real ainda nÃ£o entregue pela equipe de Cartografia", color: C.ALERT },
  ];

  items.forEach((item, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = 0.35 + col * 6.48, y = 1.42 + row * 1.12;
    s.addShape("rect", { x, y, w: 6.2, h: 1.0, fill: { color: C.WHITE }, line: { color: C.STEEL, width: 0.3 }, rectRadius: 0.06 });
    s.addShape("rect", { x, y, w: 0.07, h: 1.0, fill: { color: item.color }, line: { type: "none" } });
    // status badge
    s.addShape("rect", { x: x + 3.8, y: y + 0.12, w: 2.3, h: 0.3, fill: { color: item.color }, line: { type: "none" }, rectRadius: 0.04 });
    s.addText(item.status, { x: x + 3.8, y: y + 0.12, w: 2.3, h: 0.3, fontFace: "Calibri", fontSize: 9, bold: true, color: C.WHITE, align: "center", valign: "middle" });
    s.addText(item.area, { x: x + 0.18, y: y + 0.1, w: 3.55, h: 0.32, fontFace: "Cambria", fontSize: 11, bold: true, color: C.NAVY, align: "left" });
    s.addText(item.detail, { x: x + 0.18, y: y + 0.45, w: 5.88, h: 0.45, fontFace: "Calibri", fontSize: 9.5, color: C.SLATE, valign: "top", wrap: true });
  });
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 22 â€” DESAFIOS TÃ‰CNICOS EM ABERTO
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  s.background = { color: C.LIGHT };
  header(s, "Desafios TÃ©cnicos em Aberto", "O que falta e o que foi resolvido desde a VE");
  footerBrand(s, "22");

  const challenges = [
    {
      title: "FixaÃ§Ã£o FÃ­sica â€” PARCIALMENTE RESOLVIDO",
      body: "Espelho refletor validou a integraÃ§Ã£o projetor+Kinect no caixÃ£o antigo.\nNovo caixÃ£o em marcenaria construÃ­do â€” pronto para fixaÃ§Ã£o definitiva.\nPrÃ³ximo passo: migrar e fixar tudo na nova estrutura para a VF.",
      color: C.GOLD, icon: "ðŸ”§", status: "Em progresso",
    },
    {
      title: "ProjeÃ§Ã£o Real sobre Areia â€” PARCIALMENTE RESOLVIDO",
      body: "ProjeÃ§Ã£o colorida validada com espelho no caixÃ£o antigo.\nCores vermelho/azul/verde respondendo em tempo real ao Kinect.\nPendente: recalibrar na nova estrutura definitiva do caixÃ£o.",
      color: C.GOLD, icon: "ðŸ“½", status: "Em progresso",
    },
    {
      title: "MDE CartogrÃ¡fico Real (GeoTIFF AMAN)",
      body: "Arquivo do levantamento da AMAN ainda nÃ£o disponÃ­vel.\nSistema 100% pronto para receber o GeoTIFF (AdaptadorMDE).\nFallback sintÃ©tico (Cubo Central) funciona em demonstraÃ§Ãµes.",
      color: C.ALERT, icon: "ðŸ—º", status: "Pendente",
    },
    {
      title: "CalibraÃ§Ã£o Final na Nova Estrutura",
      body: "Kinect e projetor ainda nÃ£o fixados definitivamente.\nCalibraÃ§Ã£o da tampa deve ser repetida apÃ³s fixaÃ§Ã£o final.\nParÃ¢metros de Tsai serÃ£o recalculados com nova geometria.",
      color: C.INFO, icon: "ðŸ“", status: "Pendente (VF)",
    },
  ];

  challenges.forEach((c, i) => {
    const x = 0.35 + (i % 2) * 6.49, y = 1.42 + Math.floor(i / 2) * 2.72;
    s.addShape("rect", { x: x + 0.04, y: y + 0.04, w: 6.2, h: 2.5, fill: { color: C.SHADOW || "C8D0DA" }, line: { type: "none" }, rectRadius: 0.07 });
    s.addShape("rect", { x, y, w: 6.2, h: 2.5, fill: { color: C.WHITE }, line: { color: c.color, width: 1 }, rectRadius: 0.07 });
    s.addShape("rect", { x, y, w: 0.07, h: 2.5, fill: { color: c.color }, line: { type: "none" } });
    s.addText(c.icon, { x: x + 0.18, y: y + 0.1, w: 0.55, h: 0.5, fontFace: "Calibri", fontSize: 22, align: "left" });
    s.addShape("rect", { x: x + 4.2, y: y + 0.15, w: 1.88, h: 0.3, fill: { color: c.color }, line: { type: "none" }, rectRadius: 0.04 });
    s.addText(c.status, { x: x + 4.2, y: y + 0.15, w: 1.88, h: 0.3, fontFace: "Calibri", fontSize: 8.5, bold: true, color: c.color === C.GOLD ? C.NAVY : C.WHITE, align: "center", valign: "middle" });
    s.addText(c.title, { x: x + 0.18, y: y + 0.65, w: 5.9, h: 0.42, fontFace: "Cambria", fontSize: 11, bold: true, color: C.NAVY, align: "left", wrap: true });
    s.addText(c.body, { x: x + 0.18, y: y + 1.12, w: 5.9, h: 1.28, fontFace: "Calibri", fontSize: 10, color: C.SLATE, valign: "top", wrap: true });
  });
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 23 â€” ROADMAP DO HARDWARE (VE / VC / VF)
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  s.background = { color: C.LIGHT };
  header(s, "Roadmap do Hardware", "VE â†’ VC (atual) â†’ VF â€” evoluÃ§Ã£o da estrutura fÃ­sica");
  footerBrand(s, "23");

  const stages = [
    {
      id: "VE", label: "VerificaÃ§Ã£o Especial", period: "Jun 2026",
      items: ["Motor matemÃ¡tico funcional (Python)", "Emulador interativo (pÃ¡ virtual)", "SuÃ­te de 59 testes automatizados", "GUI CustomTkinter implementada", "Kinect integrado em modo de teste"],
      color: C.STEEL, current: false,
    },
    {
      id: "VC", label: "VerificaÃ§Ã£o de Curso", period: "Agoâ€“Set 2026",
      items: ["âœ… ProjeÃ§Ã£o validada via espelho refletor", "âœ… Kinect + projetor simultÃ¢neos (cores V/A/V)", "âœ… Novo caixÃ£o em marcenaria construÃ­do", "â³ MigraÃ§Ã£o para caixÃ£o novo", "â³ CalibraÃ§Ã£o final na nova estrutura"],
      color: C.GOLD, current: true,
    },
    {
      id: "VF", label: "VerificaÃ§Ã£o Final", period: "Novâ€“Dez 2026",
      items: ["Sistema 100% integrado no caixÃ£o definitivo", "MDE real (GeoTIFF AMAN) integrado", "CalibraÃ§Ã£o final validada em campo", "Entrega Ã  SeÃ§Ã£o de SimulaÃ§Ã£o da AMAN", "DocumentaÃ§Ã£o de transferÃªncia completa"],
      color: C.SUCCESS, current: false,
    },
  ];

  stages.forEach((st, i) => {
    const x = 0.35 + i * 4.34;
    const bg = st.current ? C.NAVY : C.WHITE;
    const textColor = st.current ? C.WHITE : C.NAVY;
    s.addShape("rect", { x: x + 0.04, y: 1.45, w: 4.1, h: 5.55, fill: { color: C.SHADOW || "C8D0DA" }, line: { type: "none" }, rectRadius: 0.08 });
    s.addShape("rect", { x, y: 1.42, w: 4.1, h: 5.55, fill: { color: bg }, line: { color: st.color, width: st.current ? 2 : 1 }, rectRadius: 0.08 });
    // badge estÃ¡gio
    s.addShape("rect", { x: x + 0.7, y: 1.55, w: 2.7, h: 0.55, fill: { color: st.color }, line: { type: "none" }, rectRadius: 0.06 });
    s.addText(st.id, { x: x + 0.7, y: 1.55, w: 2.7, h: 0.55, fontFace: "Cambria", fontSize: 18, bold: true, color: st.current ? C.NAVY : C.WHITE, align: "center", valign: "middle" });
    s.addText(st.label, { x: x + 0.12, y: 2.18, w: 3.86, h: 0.32, fontFace: "Cambria", fontSize: 11, bold: true, color: st.current ? C.GOLD : C.NAVY, align: "center" });
    s.addText(st.period, { x: x + 0.12, y: 2.5, w: 3.86, h: 0.28, fontFace: "Calibri", fontSize: 10, italic: true, color: st.current ? C.STEEL : C.STEEL, align: "center" });
    hRule(s, x + 0.3, 2.84, 3.5, st.color, 1);
    st.items.forEach((item, j) => {
      s.addText(item, { x: x + 0.22, y: 2.98 + j * 0.72, w: 3.66, h: 0.65, fontFace: "Calibri", fontSize: 10, color: st.current ? C.WHITE : C.SLATE, valign: "top", wrap: true });
    });
    if (st.current) {
      s.addShape("rect", { x: x + 0.5, y: 6.7, w: 3.1, h: 0.18, fill: { color: C.GOLD }, line: { type: "none" }, rectRadius: 0.04 });
      s.addText("â—€ ESTÃGIO ATUAL", { x: x + 0.5, y: 6.7, w: 3.1, h: 0.18, fontFace: "Calibri", fontSize: 8, bold: true, color: C.NAVY, align: "center", valign: "middle" });
    }
  });
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 24 â€” CRONOGRAMA DO PROJETO
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  s.background = { color: C.LIGHT };
  header(s, "Cronograma do Projeto", "EvoluÃ§Ã£o mensal das entregas â€” destaque atual: Agoâ€“Set 2026 (VC)");
  footerBrand(s, "24");

  const meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
  const atividades = [
    { label: "Levantamento de Requisitos", start: 0, end: 2, color: C.STEEL },
    { label: "Motor MatemÃ¡tico (RANSAC/SVD/Grade)", start: 1, end: 5, color: C.NAVY },
    { label: "Testes Automatizados (TDD)", start: 2, end: 6, color: C.INFO },
    { label: "GUI (CustomTkinter) + Emulador", start: 4, end: 6, color: C.STEEL },
    { label: "IntegraÃ§Ã£o Kinect + Projetor (VEâ†’VC)", start: 5, end: 8, color: C.GOLD },
    { label: "Espelho Refletor + CaixÃ£o Novo", start: 6, end: 8, color: C.GOLD },
    { label: "DocumentaÃ§Ã£o e Guia", start: 3, end: 9, color: C.STEEL },
    { label: "IntegraÃ§Ã£o Final (caixÃ£o novo)", start: 8, end: 10, color: C.SUCCESS },
    { label: "MDE Real (GeoTIFF AMAN)", start: 9, end: 11, color: C.SUCCESS },
    { label: "ApresentaÃ§Ã£o Final (VF)", start: 10, end: 11, color: C.SUCCESS },
  ];

  const gx = 2.85, gy = 1.38, gw = 10.0, gh = 5.75;
  const colW = gw / 12, rowH = gh / (atividades.length + 1);

  // header de meses
  meses.forEach((m, i) => {
    const isVC = i === 7 || i === 8;
    if (isVC) {
      s.addShape("rect", { x: gx + i * colW, y: gy, w: colW, h: rowH, fill: { color: C.GOLD }, line: { type: "none" } });
    }
    s.addText(m, {
      x: gx + i * colW, y: gy, w: colW, h: rowH,
      fontFace: "Calibri", fontSize: 9, bold: isVC, color: isVC ? C.NAVY : C.WHITE,
      align: "center", valign: "middle",
    });
  });
  // fundo header
  s.addShape("rect", { x: gx, y: gy, w: gw, h: rowH, fill: { color: C.NAVY }, line: { type: "none" } });
  // redesenhar header sobre fundo
  meses.forEach((m, i) => {
    const isVC = i === 7 || i === 8;
    if (isVC) s.addShape("rect", { x: gx + i * colW, y: gy, w: colW, h: rowH, fill: { color: C.GOLD }, line: { type: "none" } });
    s.addText(m, { x: gx + i * colW, y: gy, w: colW, h: rowH, fontFace: "Calibri", fontSize: 9, bold: isVC, color: isVC ? C.NAVY : C.WHITE, align: "center", valign: "middle" });
  });

  // label coluna
  s.addShape("rect", { x: 0.35, y: gy, w: 2.4, h: rowH, fill: { color: C.NAVY }, line: { type: "none" } });
  s.addText("Atividade", { x: 0.35, y: gy, w: 2.4, h: rowH, fontFace: "Calibri", fontSize: 9, bold: true, color: C.GOLD, align: "center", valign: "middle" });

  // atividades
  atividades.forEach((at, ri) => {
    const ry = gy + rowH * (ri + 1);
    const bg = ri % 2 === 0 ? "F8F9FA" : C.WHITE;
    s.addShape("rect", { x: 0.35, y: ry, w: 2.4, h: rowH, fill: { color: bg }, line: { color: C.STEEL, width: 0.2 } });
    s.addText(at.label, { x: 0.38, y: ry, w: 2.34, h: rowH, fontFace: "Calibri", fontSize: 8.5, color: C.SLATE, align: "left", valign: "middle", wrap: true });
    s.addShape("rect", { x: gx, y: ry, w: gw, h: rowH, fill: { color: bg }, line: { color: C.STEEL, width: 0.2 } });
    // barra de Gantt
    const bx = gx + at.start * colW;
    const bw = (at.end - at.start + 1) * colW - 0.04;
    s.addShape("rect", { x: bx + 0.02, y: ry + 0.05, w: bw, h: rowH - 0.12, fill: { color: at.color }, line: { type: "none" }, rectRadius: 0.03 });
  });

  // legenda VC
  s.addShape("rect", { x: 0.35, y: 7.05, w: 12.63, h: 0.22, fill: { color: "none" }, line: { type: "none" } });
  s.addText("Dourado = EstÃ¡gio VC (atual)  Â·  Verde = EstÃ¡gio VF  Â·  Azul = Eng. ComputaÃ§Ã£o  Â·  Cinza = Transversal", {
    x: 0.35, y: 7.05, w: 12.63, h: 0.22, fontFace: "Calibri", fontSize: 8.5, italic: true, color: C.STEEL, align: "center",
  });
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 25 â€” PRÃ“XIMOS PASSOS
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  s.background = { color: C.LIGHT };
  header(s, "PrÃ³ximos Passos â€” Rumo Ã  VF", "Metas para a VerificaÃ§Ã£o Final (Novâ€“Dez 2026)");
  footerBrand(s, "25");

  const passos = [
    { n: "1", title: "MigraÃ§Ã£o para o CaixÃ£o Novo", body: "Transferir toda a eletrÃ´nica (Kinect + espelho + projetor) para a estrutura de marcenaria.\nFixar definitivamente o sensor e o sistema de projeÃ§Ã£o com suportes estÃ¡veis.", icon: "ðŸªµ", color: C.GOLD },
    { n: "2", title: "CalibraÃ§Ã£o Final na Nova Estrutura", body: "Realizar calibraÃ§Ã£o da tampa com as dimensÃµes corretas do novo caixÃ£o.\nAtualizar parÃ¢metros Tsai do projetor com a nova geometria de montagem.", icon: "ðŸ“", color: C.NAVY },
    { n: "3", title: "IntegraÃ§Ã£o do MDE Real (GeoTIFF AMAN)", body: "Receber o arquivo de levantamento cartogrÃ¡fico da equipe de Cartografia.\nValidar a leitura pelo AdaptadorMDE e ajustar escala para o caixÃ£o fÃ­sico.", icon: "ðŸ—º", color: C.INFO },
    { n: "4", title: "ValidaÃ§Ã£o de Campo e Entrega", body: "DemonstraÃ§Ã£o ao vivo com operador real da SeÃ§Ã£o de SimulaÃ§Ã£o da AMAN.\nEntrega do sistema, documentaÃ§Ã£o e guia de instalaÃ§Ã£o para usuÃ¡rio final.", icon: "âœ…", color: C.SUCCESS },
  ];

  passos.forEach((p, i) => {
    const y = 1.42 + i * 1.35;
    s.addShape("rect", { x: 0.55, y: y + 0.04, w: 12.23, h: 1.22, fill: { color: C.SHADOW || "C8D0DA" }, line: { type: "none" }, rectRadius: 0.07 });
    s.addShape("rect", { x: 0.5, y, w: 12.23, h: 1.22, fill: { color: C.WHITE }, line: { color: p.color, width: 0.5 }, rectRadius: 0.07 });
    s.addShape("rect", { x: 0.5, y, w: 0.07, h: 1.22, fill: { color: p.color }, line: { type: "none" } });
    s.addShape("ellipse", { x: 0.72, y: y + 0.35, w: 0.52, h: 0.52, fill: { color: p.color }, line: { type: "none" } });
    s.addText(p.n, { x: 0.72, y: y + 0.35, w: 0.52, h: 0.52, fontFace: "Cambria", fontSize: 16, bold: true, color: C.WHITE, align: "center", valign: "middle" });
    s.addText(p.icon + "  " + p.title, { x: 1.35, y: y + 0.07, w: 11.2, h: 0.38, fontFace: "Cambria", fontSize: 13, bold: true, color: p.color, align: "left" });
    s.addText(p.body, { x: 1.35, y: y + 0.48, w: 11.2, h: 0.65, fontFace: "Calibri", fontSize: 10.5, color: C.SLATE, valign: "top", wrap: true });
  });
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// SLIDE 26 â€” ENCERRAMENTO
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
{
  const s = pptx.addSlide();
  s.background = { color: "0f2540" };
  s.addShape("rect", { x: 0, y: 0, w: 13.33, h: 0.12, fill: { color: C.GOLD }, line: { type: "none" } });
  s.addShape("rect", { x: 0, y: 7.38, w: 13.33, h: 0.12, fill: { color: C.GOLD }, line: { type: "none" } });
  s.addShape("rect", { x: 0.5, y: 1.0, w: 12.33, h: 5.4, fill: { color: C.NAVY }, line: { color: C.GOLD, width: 1 }, rectRadius: 0.12 });

  s.addText("Agradecimentos", { x: 0.7, y: 1.3, w: 11.93, h: 0.48, fontFace: "Cambria", fontSize: 22, bold: true, color: C.GOLD, align: "center" });
  hRule(s, 3.0, 1.82, 7.33, C.GOLD, 1);

  s.addText([
    "Ao corpo docente orientador pelo acompanhamento e direcionamento tÃ©cnico.",
    "Ã€ SeÃ§Ã£o de SimulaÃ§Ã£o da AMAN pela confianÃ§a, pela demanda real e pela disponibilidade em validar o sistema.",
    "Ã€ equipe de Cartografia pelo suporte com os dados de terreno.",
  ].join("\n\n"), { x: 0.9, y: 1.95, w: 11.53, h: 1.9, fontFace: "Calibri", fontSize: 13, color: C.WHITE, align: "center", valign: "middle", wrap: true });

  hRule(s, 3.0, 3.92, 7.33, C.STEEL, 1);

  s.addText("Ã€ disposiÃ§Ã£o para os questionamentos da banca examinadora.", {
    x: 0.7, y: 4.1, w: 11.93, h: 0.55, fontFace: "Cambria", fontSize: 18, bold: true, italic: true, color: C.GOLD, align: "center",
  });

  // integrantes
  s.addText("Raquel  Â·  Integrante 2  Â·  Integrante 3  Â·  Integrante 4", {
    x: 0.7, y: 4.78, w: 11.93, h: 0.35, fontFace: "Calibri", fontSize: 12, color: C.STEEL, align: "center",
  });
  s.addText("Orientador: Prof. [Nome]", {
    x: 0.7, y: 5.13, w: 11.93, h: 0.3, fontFace: "Calibri", fontSize: 11, color: C.STEEL, align: "center",
  });
  s.addText("Academia Militar das Agulhas Negras â€” Engenharia de ComputaÃ§Ã£o e EletrÃ´nica â€” 2026", {
    x: 0.7, y: 5.58, w: 11.93, h: 0.3, fontFace: "Calibri", fontSize: 10, italic: true, color: "7B8FA1", align: "center",
  });
}

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
// GERAR ARQUIVO
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
const OUTPUT = "../Apresentacao_PFC_Caixao_de_Areia.pptx";

pptx.writeFile({ fileName: OUTPUT })
  .then(() => {
    console.log(`\nâœ“  Gerado com sucesso: ${OUTPUT}`);
    console.log("   Slides: 26");
    console.log("   Novos slides (VC): Espelho Refletor (18), CaixÃ£o Novo (19)");
    console.log("   Slides atualizados: Capa, Cronograma, Roadmap, Estado Atual, Desafios");
    console.log("   Placeholders de foto: 4 (2 no slide 18, 2 no slide 19)\n");
  })
  .catch(err => {
    console.error("Erro ao gerar PPTX:", err);
    process.exit(1);
  });

