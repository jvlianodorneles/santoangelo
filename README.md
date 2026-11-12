# Santo Ângelo Isométrica

Mapa interativo em pixel-art 3D de **Santo Ângelo, Rio Grande do Sul, Brasil**, cobrindo o Centro Histórico, a **Catedral Angelopolitana** e a **Praça Pinheiro Machado**.

Construído a partir de dados abertos e renderização procedural isométrica, adaptado do projeto pioneiro [Isometric Helenaveen](https://github.com/jankeesvw/isometric-helenaveen) por [@jankeesvw](https://x.com/jankeesvw).

Disponível online em: [https://jvlianodorneles.github.io/santoangelo/](https://jvlianodorneles.github.io/santoangelo/)

---

## 🏛️ Destaques

- **Catedral Angelopolitana em 3D**: Torres sineiras de 32 metros, arcos e relevos esculpidos dos padroeiros e arcanjos, naves principais e cruzes missioneiras.
- **Centro Histórico e Praça Pinheiro Machado**: Museu Histórico das Missões, Memorial Coluna Prestes, Teatro Antônio Sepp, Sítio Arqueológico / Museu a Céu Aberto e Monumento a Sepé Tiaraju.
- **Tráfego Dinâmico**: Mais de 1.800 faixas de tráfego com circulação simulada de carros, ônibus e pedestres pelas vias reais de Santo Ângelo.
- **4 Ângulos de Câmera ($45^\circ, 135^\circ, 225^\circ, 315^\circ$)**: Giro suave da perspectiva isométrica 2:1 com agulha de bússola georreferenciada.
- **Ciclo Dia e Noite**: Alternância para o entardecer com lanternas acesas na praça central e faróis de veículos.
- **Tour Histórico**: 8 paradas cronológicas contando a evolução de Santo Ângelo desde a fundação da redução jesuítica em 1706 até os dias atuais.

---

## 🛰️ Pipeline de Dados Abertos

O pipeline original holandês (3D BAG, BGT, AHN, PDOK) foi adaptado para a realidade de dados geoespaciais abertos no Brasil:

1. **Sistema de Coordenadas Métrico**:
   - Projeção **SIRGAS 2000 / UTM Zone 21S ([EPSG:31981](https://epsg.io/31981))**, garantindo métrica exata em metros sem distorções locais.
   - Algoritmo fechado de projeção Transverse Mercator implementado em `scripts/geo.py`.
2. **Edificações e Malha Viária (OpenStreetMap)**:
   - Extração via OpenStreetMap API dos footprints de edificações, vias urbanas e pontos de interesse com alturas estimadas e formas de telhado.
3. **Ortofoto Aérea**:
   - Esri World Imagery (alta resolução em nível de zoom 18) cobrindo a área de $2{,}0\text{ km} \times 2{,}0\text{ km}$ ($4{,}0\text{ km}^2$).
4. **Relevo e Árvores**:
   - Dados de elevação AWS Terrarium (SRTM/Copernicus) e índice de dossel ExG (*Excess Green*) para detectar e posicionar mais de 23.000 árvores individuais.
5. **Renderizador e Visualizador**:
   - Renderização em Three.js com shaders personalizados (cel-shading, filtros Kuwahara, contornos estilizados) executado em Chromium headless (Vulkan/GPU).
   - Visualizador web com OpenSeadragon e pirâmides de azulejos WebP Deep Zoom.

---

## 🛠️ Como Executar

### Pré-requisitos
- Node.js 20+ e npm
- Python 3.12+ (gerenciado via `uv`)
- `libvips` (`vips dzsave`)
- Chromium

### Construção Completa
```bash
# Instalar dependências
npm install
uv venv --python 3.12
source .venv/bin/activate
pip install -r requirements.txt

# Executar pipeline completo (dados -> modelos 3D -> renderização -> azulejos)
./build.sh

# Testar localmente
python3 -m http.server 8000 -d site
```

### Publicação no GitHub Pages
```bash
./deploy.sh
```

---

## 📜 Licenças e Créditos

- **Código Base**: [jankeesvw/isometric-helenaveen](https://github.com/jankeesvw/isometric-helenaveen) (MIT).
- **Vias e Edificações**: © [Colaboradores do OpenStreetMap](https://www.openstreetmap.org/) (ODbL 1.0).
- **Imagens de Satélite/Aéreas**: Esri, Maxar, Earthstar Geographics.
- **Elevação**: AWS Terrarium (Open Data / CC0).
- **Trilha Sonora**: *My Street* por congusbongus (OpenGameArt, CC0).
- **Fotografias Históricas**: Wikimedia Commons (CC BY-SA / Domínio Público).
