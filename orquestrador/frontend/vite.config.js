import { fileURLToPath, URL } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const root = fileURLToPath(new URL(".", import.meta.url));

/**
 * Build multi-página: cada tela mantém seu próprio HTML e CSS, como no
 * frontend estático original (preserva URLs e evita conflito de estilos).
 * O resultado em `dist/` é servido pelo orquestrador na mesma origem.
 */
export default defineConfig({
  root,
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/orquestracao": "http://localhost:8200",
      "/api": "http://localhost:8200",
      "/health": "http://localhost:8200",
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        index: `${root}index.html`,
        chat: `${root}chat.html`,
        resultados: `${root}resultados.html`,
        solucao: `${root}solucao.html`,
        teste: `${root}teste.html`,
        oportunidade: `${root}oportunidade.html`,
        admin: `${root}admin.html`,
        "admin-demandas": `${root}admin-demandas.html`,
        "admin-demanda": `${root}admin-demanda.html`,
        "admin-radar": `${root}admin-radar.html`,
        "admin-padroes": `${root}admin-padroes.html`,
      },
    },
  },
});
