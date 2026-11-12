# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
"""Named places of Santo Ângelo, RS, Brazil:
Style overrides and 3D geometry for landmarks, plus the viewer's place cards and series.

Output: data/build/landmarks.json
"""

import json
from pathlib import Path
import numpy as np

from config import BUILD, RAW
from geo import wgs_to_rd

INFO = (
    "note", "kind", "address", "web", "monument", "wiki", "image", "image_credit",
    "story", "source", "series", "stop",
)

BUILDINGS = [
    {
        "name": "Catedral Angelopolitana",
        "note": "Catedral em arenito missioneiro, inspirada na redução de São Miguel Arcanjo",
        "kind": "Patrimônio Histórico e Religioso · 1929",
        "stop": "Catedral Angelopolitana",
        "at": (768528.0, 6865980.0),
        "style": "church",
        "wall": (195, 128, 92),
        "roof": (155, 85, 65),
        "tower": {"x": 768518.0, "y": 6865954.0, "w": 6.2, "body": 24.0, "top": 32.0, "cross": True},
        "series": "missoes",
        "story": "Erguida a partir de 1929 sobre os alicerces da antiga igreja da redução jesuítica de Santo Ângelo Custódio (1706), a Catedral Angelopolitana é o símbolo máximo da cidade. Sua imponente fachada em arenito missioneiro foi desenhada em estilo barroco missioneiro, inspirada nas ruínas de São Miguel Arcanjo. Suas torres sineiras abrigam sinos históricos e são ladeadas por pórticos esculpidos e estátuas dos Apóstolos esculpidas em pedra.",
    },
    {
        "name": "Museu Histórico das Missões",
        "note": "Museu Municipal Dr. José Olavo Machado em casarão colonial do século XIX",
        "kind": "Museu Histórico e Arqueológico",
        "stop": "Museu das Missões",
        "at": (768492.5, 6865951.3),
        "style": "house",
        "wall": (238, 230, 214),
        "roof": (172, 92, 68),
        "frame": (140, 70, 50),
        "series": "missoes",
        "story": "Localizado na esquina da Praça Pinheiro Machado, o museu ocupa um dos mais antigos casarões históricos de Santo Ângelo, outrora residência do diretor da colônia. Seu acervo reúne preciosidades arqueológicas do período jesuítico-guarani, peças sacras esculpidas em madeira policromada, sinos de bronze da antiga redução e vestígios indígenas.",
    },
    {
        "name": "Teatro Municipal Antônio Sepp",
        "note": "Principal centro cultural e de artes cênicas da região das Missões",
        "kind": "Teatro Municipal",
        "stop": "Teatro Antônio Sepp",
        "at": (768940.7, 6866501.4),
        "style": "school",
        "wall": (212, 198, 180),
        "roof": (110, 112, 118),
        "series": "cultura",
        "story": "Batizado em homenagem ao padre jesuíta Anton Sepp, que introduziu a fundição de ferro e a música instrumental nas Missões, o Teatro Antônio Sepp é o epicentro cultural de Santo Ângelo, sediando festivais internacionais de música missioneira, o Canto Missioneiro e espetáculos teatrais.",
    },
    {
        "name": "Memorial Coluna Prestes",
        "note": "Antiga Estação Ferroviária de 1921 e museu histórico da Coluna Prestes",
        "kind": "Memorial e Museu Ferroviário · 1921",
        "stop": "Memorial Coluna Prestes",
        "at": (769013.3, 6866525.2),
        "style": "house",
        "wall": (185, 142, 102),
        "roof": (148, 80, 62),
        "series": "historia",
        "story": "Instalado no prédio histórico da Estação Ferroviária inaugurada em 1921, o memorial documenta o levante militar revolucionário de outubro de 1924, deflagrado em Santo Ângelo sob o comando do capitão Luís Carlos Prestes, que deu início à épica marcha de 25 mil quilômetros pelo interior do Brasil.",
    },
    {
        "name": "Colégio Marista Santo Ângelo",
        "note": "Tradicional instituição de ensino fundada no coração da cidade",
        "kind": "Instituição Educacional",
        "at": (768939.3, 6865850.8),
        "style": "school",
        "wall": (210, 205, 195),
        "roof": (168, 88, 66),
        "series": "cultura",
        "story": "Com ampla presença educacional e comunitária, o complexo do Colégio Marista e Ginásio Champagnat representa quase um século de dedicação ao ensino e formação humanística nas Missões.",
    },
    {
        "name": "Colégio Teresa Verzeri",
        "note": "Instituição centenária das Filhas do Sagrado Coração de Jesus",
        "kind": "Instituição Educacional e Religiosa",
        "at": (768021.9, 6866472.6),
        "style": "school",
        "wall": (224, 218, 206),
        "roof": (165, 85, 65),
        "series": "cultura",
        "story": "Fundado no início do século XX pela congregação das Filhas do Sagrado Coração de Jesus, o Colégio Teresa Verzeri é uma das referências históricas na educação da mocidade missioneira.",
    },
    {
        "name": "Câmara Municipal de Vereadores",
        "note": "Sede do Poder Legislativo Angelopolitano",
        "kind": "Poder Legislativo",
        "at": (768485.6, 6865991.0),
        "style": "house",
        "wall": (230, 226, 218),
        "roof": (120, 122, 126),
        "series": "historia",
        "story": "Localizada no centro cívico e histórico de Santo Ângelo, defronte à Praça Pinheiro Machado, abriga os debates e a memória democrática do município.",
    },
]

POINTS = [
    {
        "name": "Praça Pinheiro Machado (Centro Histórico)",
        "note": "Coração da redução de 1706 com sítio arqueológico a céu aberto",
        "kind": "Centro Histórico e Praça Monumental",
        "stop": "Praça Pinheiro Machado",
        "at": (768525.0, 6865900.0),
        "series": "missoes",
        "story": "A Praça Pinheiro Machado é o exato núcleo fundacional de Santo Ângelo Custódio, fundado em 1706 pelo padre Diogo Haze. Sob suas árvores centenárias e alamedas, escavações arqueológicas protegidas por cúpulas de vidro expõem as fundações jesuíticas, os túneis subterrâneos e os vestígios da última das Sete Reduções das Missões Orientais.",
    },
    {
        "name": "Sítio Arqueológico / Museu a Céu Aberto",
        "note": "Escavações com as fundações originais em pedra grés da redução de 1706",
        "kind": "Sítio Arqueológico",
        "stop": "Sítio Arqueológico",
        "at": (768535.0, 6865915.0),
        "series": "missoes",
        "story": "Durante obras de requalificação urbana, foram descobertos os pisos, canalizações e alicerces de pedra da antiga igreja missioneira e das oficinas dos índios guaranis. Hoje preservadas como museu a céu aberto no calçadão em frente à catedral.",
    },
    {
        "name": "Cruz Missioneira",
        "note": "Símbolo máximo das Missões Jesuíticas Guaranis de duas hastes",
        "kind": "Monumento Histórico",
        "at": (768520.0, 6865930.0),
        "series": "missoes",
        "story": "A Cruz Missioneira (Cruz de Caravaca de haste dupla) é o símbolo espiritual e identitário do povo missioneiro, erguida na praça principal em memória da fé e da história dos povos guaranis.",
    },
    {
        "name": "Monumento a Sepé Tiaraju",
        "note": "Homenagem ao líder guerreiro guarani: 'Esta terra tem dono!'",
        "kind": "Monumento e Patrimônio Histórico",
        "stop": "Monumento a Sepé Tiaraju",
        "at": (768550.0, 6865880.0),
        "series": "missoes",
        "story": "Monumento dedicado a Sepé Tiaraju, alferes-mor e herói dos Sete Povos que liderou a resistência guarani contra a demarcação colonial imposta pelo Tratado de Madri na Guerra Guaranítica de 1756, imortalizando a célebre frase: 'Esta terra tem dono!'.",
    },
    {
        "name": "Praça Ricardo Leônidas Ribas (Praça do Brique)",
        "note": "Cenário do tradicional Brique da Praça aos domingos",
        "kind": "Praça e Espaço Cultural Comunitário",
        "stop": "Praça do Brique",
        "at": (768400.0, 6865200.0),
        "series": "cultura",
        "story": "Conhecida carinhosamente por todos os angelopolitanos como Praça do Brique, reúne todos os domingos pela manhã artistas, músicos, artesãos e moradores para saborear chimarrão, música tradicionalista e comércio de antiguidades desde 1991.",
    },
    {
        "name": "Trem Maria Fumaça",
        "note": "Locomotiva a vapor histórica preservada no pátio ferroviário",
        "kind": "Patrimônio Ferroviário",
        "at": (769025.0, 6866540.0),
        "series": "historia",
        "story": "Autêntica locomotiva a vapor (Maria Fumaça) preservada sobre os trilhos junto ao Memorial Coluna Prestes, testemunho do auge ferroviário que transportava a produção agrícola e passageiros no noroeste gaúcho.",
    },
]

MASTS = []

CATEGORIES = [
    ("missoes", "Herança Missioneira", [
        "Catedral Angelopolitana",
        "Museu Histórico das Missões",
        "Praça Pinheiro Machado (Centro Histórico)",
        "Sítio Arqueológico / Museu a Céu Aberto",
        "Cruz Missioneira",
        "Monumento a Sepé Tiaraju",
    ]),
    ("historia", "História e Memória", [
        "Memorial Coluna Prestes",
        "Trem Maria Fumaça",
        "Câmara Municipal de Vereadores",
    ]),
    ("cultura", "Cultura e Tradição", [
        "Teatro Municipal Antônio Sepp",
        "Praça Ricardo Leônidas Ribas (Praça do Brique)",
        "Colégio Teresa Verzeri",
        "Colégio Marista Santo Ângelo",
    ]),
]


def point_in_ring(x, y, ring):
    n, inside = len(ring), False
    p1x, p1y = ring[0]
    for i in range(n + 1):
        p2x, p2y = ring[i % n]
        if y > min(p1y, p2y) and y <= max(p1y, p2y) and x <= max(p1x, p2x):
            if p1y != p2y:
                xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
            if p1x == p2x or x <= xinters:
                inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def main():
    rings = []
    for line in open(RAW / "3dbag.jsonl"):
        feat = json.loads(line)
        pid = feat["id"]
        obj = feat["CityObjects"][pid]
        b = obj["geometry"][0]["boundaries"][0][0]
        verts = np.array(feat["vertices"])
        rings.append((pid, verts[b][:, :2], obj["attributes"]))

    out = {"places": [], "buildings": {}, "hotspots": [], "masts": [], "categories": []}

    for b in BUILDINGS:
        x, y = b["at"] if "at" in b else wgs_to_rd(*b["latlon"])
        pid, attrs = None, None
        for rid, ring, a in rings:
            if point_in_ring(x, y, ring):
                pid, attrs = rid, a
                break
        if pid is None:
            d = [(np.hypot(*(ring.mean(0) - (x, y))), rid, a) for rid, ring, a in rings]
            if d:
                dist, pid, attrs = min(d, key=lambda t: t[0])
                if dist > 60:
                    pid = None

        height = ((attrs or {}).get("b3_h_dak_max") or 8.0)
        if "tower" in b:
            height = b["tower"]["top"]
        out["places"].append({"name": b["name"], "note": b.get("note"), "x": x, "y": y, "h": round(height, 1)})
        if pid and "style" in b:
            out["buildings"][pid] = {k: v for k, v in b.items() if k not in ("at", "latlon", *INFO)}
        if pid:
            out["hotspots"].append({"name": b["name"], "pid": pid, "x": x, "y": y, **{k: b[k] for k in INFO if k in b}})
        else:
            out["hotspots"].append({"name": b["name"], "x": x, "y": y, **{k: b[k] for k in INFO if k in b}})
        print(f"{b['name']}: {pid or 'no building'}")

    for p in POINTS:
        x, y = p["at"] if "at" in p else wgs_to_rd(*p["latlon"])
        out["places"].append({"name": p["name"], "note": p.get("note"), "x": x, "y": y, "h": 2.0})
        out["hotspots"].append({"name": p["name"], "x": x, "y": y, **{k: p[k] for k in INFO if k in p}})

    names = {h["name"] for h in out["hotspots"]}
    for key, label, members in CATEGORIES:
        out["categories"].append({"key": key, "label": label, "names": [m for m in members if m in names]})

    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "landmarks.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"Generated landmarks.json: {len(out['places'])} places, {len(out['hotspots'])} hotspots.")


if __name__ == "__main__":
    main()
