# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Santo Ângelo Histórica: Roteiro guiado pelas eras das Missões e a formação angelopolitana.

Fontes históricas: Arquivo Histórico Municipal de Santo Ângelo, IPHAN, Wikimedia Commons.
Fotos sob licenças abertas (CC BY-SA ou Domínio Público).

Output: data/build/history.json e data/build/history/*.jpg
"""

import hashlib
import json
import re
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

from config import BUILD, CX, CY
from geo import wgs_to_rd

UA = {"User-Agent": "IsometricSantoAngelo/1.0 (https://github.com/dorneles)"}

IPHAN = ("IPHAN - Instituto do Patrimônio Histórico e Artístico Nacional", "http://portal.iphan.gov.br")
COMMONS = ("Wikimedia Commons", "https://commons.wikimedia.org")

STOPS = [
    {
        "year": "1706",
        "title": "Fundação da Redução de Santo Ângelo Custódio",
        "at": (768525.0, 6865900.0),
        "zoom": 0.8,
        "text": "Em 1706, o padre jesuíta belga Diogo Haze funda a redução de Santo Ângelo Custódio, a última e mais oriental das Sete Reduções Jesuíticas dos Guaranis. O povoado floresceu com milhares de indígenas, desenvolvendo agricultura, música sacra, escultura e fundição.",
        "photos": [
            ("Praça_Pinheiro_Machado,_Santo_Ângelo.jpg", "Praça Pinheiro Machado, antigo centro cívico e religioso da redução jesuítica (CC BY-SA 4.0)"),
        ],
        "source": IPHAN,
    },
    {
        "year": "1756",
        "title": "A Guerra Guaranítica e Sepé Tiaraju",
        "at": (768550.0, 6865880.0),
        "zoom": 1.2,
        "text": "Com o Tratado de Madri de 1750, Portugal e Espanha ordenaram a expulsão dos guaranis das Missões Orientais. O alferes-mor Sepé Tiaraju liderou a heroica resistência indígena contra os exércitos imperiais, imortalizando nas coxilhas a frase célebre: 'Esta terra tem dono!'.",
        "photos": [
            ("Estátua_Sepé_Tiaraju.jpg", "Estátua em homenagem ao herói guarani Sepé Tiaraju (CC BY-SA 3.0)"),
        ],
        "source": ("Memória das Missões", "https://pt.wikipedia.org/wiki/Sep%C3%A9_Tiaraju"),
    },
    {
        "year": "1855",
        "title": "A Nova Povoação e a Chegada dos Imigrantes",
        "at": (768492.5, 6865951.3),
        "zoom": 1.0,
        "text": "Após a destruição das missões, Santo Ângelo renasce em meados do século XIX como colônia militar e polo de colonização. Imigrantes alemães, italianos, poloneses e russos estabelecem-se ao redor do antigo centro histórico, integrando-se aos descendentes indígenas e tropeiros.",
        "photos": [],
        "source": ("História de Santo Ângelo", "https://santoangelo.rs.gov.br"),
    },
    {
        "year": "1921",
        "title": "A Estação Ferroviária e os Trilhos do Progresso",
        "at": (769013.3, 6866525.2),
        "zoom": 1.0,
        "text": "A inauguração da Estação Ferroviária em 1921 conecta Santo Ângelo à malha da Viação Férrea do Rio Grande do Sul. O pátio ferroviário com suas locomotivas a vapor impulsionou o comércio de trigo, erva-mate, soja e manufaturas.",
        "photos": [
            ("Memorial_Coluna_Prestes_(Santo_Ângelo,_Brasil)_.jpg", "Prédio da Antiga Estação Ferroviária de 1921, atual Memorial Coluna Prestes (CC BY-SA 4.0)"),
        ],
        "source": COMMONS,
    },
    {
        "year": "1924",
        "title": "O Levante Militar e a Coluna Prestes",
        "at": (769025.0, 6866540.0),
        "zoom": 1.1,
        "text": "Nas noites de outubro de 1924, o capitão Luís Carlos Prestes comanda no 1º Batalhão Ferroviário de Santo Ângelo a revolta tenentista. Os revolucionários gaúchos iniciaram aqui a lendária marcha de mais de 25.000 quilômetros pelo interior do país.",
        "photos": [],
        "source": ("Memorial Coluna Prestes", "https://santoangelo.rs.gov.br"),
    },
    {
        "year": "1929",
        "title": "A Construção da Catedral Angelopolitana",
        "at": (768528.0, 6865980.0),
        "zoom": 1.3,
        "text": "Em 1929 tem início a construção da imponente Catedral de Santo Ângelo, erguida sobre os próprios alicerces da antiga igreja dos jesuítas. Sua arquitetura barroco-missioneira evoca a monumentalidade de São Miguel Arcanjo, talhada no arenito róseo da região.",
        "photos": [
            ("Catedral_angelopolitana_santo_angelo.jpg", "Fachada monumental da Catedral Angelopolitana em arenito missioneiro (CC BY-SA 4.0)"),
        ],
        "source": ("Diocese de Santo Ângelo", "https://diocesedesantoangelo.org"),
    },
    {
        "year": "1980s",
        "title": "As Escavações Arqueológicas e o Museu a Céu Aberto",
        "at": (768535.0, 6865915.0),
        "zoom": 1.2,
        "text": "Trabalhos arqueológicos no subsolo da Praça Pinheiro Machado desvelaram as galerias subterrâneas, paredes de pedra e pisos da redução do século XVIII. Protegidos por estruturas envidraçadas, os vestígios formam um museu a céu aberto.",
        "photos": [],
        "source": IPHAN,
    },
    {
        "year": "1991",
        "title": "O Brique da Praça",
        "at": (768400.0, 6865200.0),
        "zoom": 1.0,
        "text": "Na arborizada Praça Ricardo Leônidas Ribas, nasce em 1991 o tradicional Brique da Praça. Todos os domingos pela manhã, o local transforma-se em ponto de encontro do chimarrão, música missioneira nativista, culinária típica e artesanato regional.",
        "photos": [],
        "source": ("Brique da Praça", "https://santoangelo.rs.gov.br"),
    },
]


def commons_thumb(filename, width=1200):
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query",
        "titles": f"File:{filename}",
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": str(width),
        "format": "json",
    })
    req = urllib.request.Request(url, headers=UA)
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read())
                pages = d.get("query", {}).get("pages", {})
                for page in pages.values():
                    ii = page.get("imageinfo", [{}])[0]
                    return ii.get("thumburl") or ii.get("url")
        except Exception:
            time.sleep(2)
    return None


def download(url):
    req = urllib.request.Request(url, headers=UA)
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read()
        except Exception:
            time.sleep(2)
    return b""


def main():
    out_dir = BUILD / "history"
    out_dir.mkdir(parents=True, exist_ok=True)
    stops = []
    for i, s in enumerate(STOPS, start=1):
        x, y = s["at"] if "at" in s else wgs_to_rd(*s["latlon"])
        stop = {
            "n": i,
            "year": s["year"],
            "title": s["title"],
            "text": s["text"],
            "x": round(x, 1),
            "y": round(y, 1),
            "h": s.get("h", 0),
            "zoom": s.get("zoom", 1.2),
            "source": {"label": s["source"][0], "url": s["source"][1]},
            "more": s.get("more"),
            "photos": [],
        }
        for k, (name, credit) in enumerate(s.get("photos", [])):
            dst = out_dir / f"{i:02d}_{k}.jpg"
            if not dst.exists():
                thumb_url = commons_thumb(name)
                if thumb_url:
                    data = download(thumb_url)
                    if data:
                        dst.write_bytes(data)
                        subprocess.run(
                            ["magick", str(dst), "-resize", "640x640>", "-quality", "85", str(dst)],
                            check=False,
                        )
            if dst.exists():
                stop["photos"].append({
                    "src": f"history/{dst.name}",
                    "credit": credit,
                    "url": f"https://commons.wikimedia.org/wiki/File:{urllib.parse.quote(name)}",
                })
        stops.append(stop)

    (BUILD / "history.json").write_text(json.dumps({"stops": stops}, ensure_ascii=False, indent=1))
    print(f"Generated history.json: {len(stops)} tour stops.")


if __name__ == "__main__":
    main()
