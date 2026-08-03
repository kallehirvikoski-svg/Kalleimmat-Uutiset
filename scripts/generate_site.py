"""
Hakee AI- ja NHL-uutiset RSS-lähteistä, antaa Claudelle (Anthropic API) tehtäväksi
valita, tiivistää ja priorisoida niistä parhaat, ja generoi staattisen index.html-sivun.
Ajetaan automaattisesti GitHub Actionsin kautta (ks. .github/workflows/update.yml).

Vaatii ympäristömuuttujan ANTHROPIC_API_KEY (GitHub-repon secret). Jos avainta ei
ole asetettu tai API-kutsu epäonnistuu, sivu näyttää raa'at otsikot varasuunnitelmana
eikä koko ajo kaadu.
"""

import html
import json
import os
from datetime import datetime, timezone

import feedparser
import requests

# Voit lisätä/poistaa/vaihtaa näitä lähteitä vapaasti.
AI_FEEDS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.artificialintelligence-news.com/feed/",
]

NHL_FEEDS = [
    "https://sports.yahoo.com/nhl/rss/",
    "https://nhl.nbcsports.com/feed/",
]

MAX_ITEMS = 5
CANDIDATE_POOL = 15  # kuinka monta tuoretta uutista tarjotaan Claudelle valittavaksi

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"  # halvin ja nopein malli, riittää tähän

AI_INSTRUCTIONS = """Sinulle annetaan lista tuoreita AI-uutisia (otsikko, kuvaus, lähde, linkki).
Valitse näistä 5 tärkeintä painottaen:
- uusia malleja ja niiden käyttökelpoisia ominaisuuksia (ei pelkkää benchmark-hypeä)
- automaatioon ja työkaluihin liittyviä uutisia (agentit, integraatiot, no-code/low-code)
- pienten yritysten ja tuotannon AI-sovelluksia
Kirjoita jokaiselle valitsemallesi uutiselle suomenkielinen 3-4 lauseen yhteenveto, joka
avaa uutisen taustaa ja merkitystä tarkemmin (ei vain toista otsikkoa).

Valitse lisäksi yksi konkreettinen AI-työkalun ominaisuus, prompting-tekniikka tai
automaatio-käyttötapa, jota lukija ei todennäköisesti vielä tunne tai hyödynnä täysin.
Selitä se 5-6 lauseessa ja anna yksi käytännön esimerkki miten sitä voisi soveltaa
pienyrityksen automaatiossa, data-analytiikassa tai tuotannon johtamisessa."""

NHL_INSTRUCTIONS = """Sinulle annetaan lista tuoreita NHL-uutisia (otsikko, kuvaus, lähde, linkki).
Valitse näistä 5 tärkeintä painottaen:
- ottelutuloksia ja niiden käännekohtia
- siirtoja, sopimuksia ja offer sheet -tilanteita
- loukkaantumisia ja kokoonpanomuutoksia
Kirjoita jokaiselle valitsemallesi uutiselle suomenkielinen 3-4 lauseen yhteenveto, joka
avaa uutisen taustaa ja merkitystä tarkemmin (ei vain toista otsikkoa)."""


def fetch_items(feeds, max_items=CANDIDATE_POOL):
    entries = []
    for url in feeds:
        try:
            parsed = feedparser.parse(url)
            source_name = parsed.feed.get("title", url)
            for entry in parsed.entries:
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                entries.append(
                    {
                        "title": entry.get("title", "Ei otsikkoa"),
                        "description": entry.get("summary", ""),
                        "link": entry.get("link", "#"),
                        "published": published,
                        "source": source_name,
                    }
                )
        except Exception as e:
            # Jos yksi lähde kaatuu, jatketaan silti muilla.
            print(f"Virhe haettaessa feediä {url}: {e}")

    entries.sort(
        key=lambda e: e["published"] if e["published"] else (0,),
        reverse=True,
    )
    return entries[:max_items]


def summarize_with_claude(instructions, raw_items, include_opetus=False):
    """Pyytää Claudelta valinnan + suomenkieliset yhteenvedot, ja valinnaisesti
    yhden opetuspätkän. Palauttaa (items, opetus)-parin, tai (None, None) jos
    API-kutsu epäonnistuu."""
    if not ANTHROPIC_API_KEY:
        print("ANTHROPIC_API_KEY puuttuu, käytetään raakoja otsikoita.")
        return None, None
    if not raw_items:
        return [], None

    candidate_text = "\n\n".join(
        f"Otsikko: {item['title']}\n"
        f"Kuvaus: {item['description'][:300]}\n"
        f"Lähde: {item['source']}\n"
        f"Linkki: {item['link']}"
        for item in raw_items
    )

    if include_opetus:
        schema_hint = (
            '{"items": [{"title": "...", "summary": "...", "source": "...", "link": "..."}], '
            '"opetus": {"title": "...", "explanation": "..."}}'
        )
    else:
        schema_hint = '{"items": [{"title": "...", "summary": "...", "source": "...", "link": "..."}]}'

    prompt = f"""{instructions}

Uutiskandidaatit:
{candidate_text}

Vastaa VAIN JSON-muodossa, ilman selityksiä, preamblea tai koodilohkomerkintöjä,
täsmälleen tässä muodossa:
{schema_hint}"""

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": ANTHROPIC_MODEL,
                "max_tokens": 2000 if include_opetus else 1600,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        response.raise_for_status()
        text = response.json()["content"][0]["text"].strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed = json.loads(text)
        items = parsed.get("items", [])[:MAX_ITEMS]
        opetus = parsed.get("opetus") if include_opetus else None
        return items, opetus
    except Exception as e:
        print(f"Claude-kutsu epäonnistui, käytetään raakoja otsikoita: {e}")
        return None, None


def get_section_items(feeds, instructions, include_opetus=False):
    raw_items = fetch_items(feeds)
    summarized, opetus = summarize_with_claude(instructions, raw_items, include_opetus)
    if summarized is not None:
        return summarized, opetus

    # Varasuunnitelma: raa'at otsikot ilman yhteenvetoa, jos API ei ole käytössä.
    fallback = []
    for item in raw_items[:MAX_ITEMS]:
        fallback.append(
            {
                "title": item["title"],
                "summary": "",
                "source": item["source"],
                "link": item["link"],
            }
        )
    return fallback, None


def render_section(title, items):
    if not items:
        return f"<section><h2>{title}</h2><p class='empty'>Ei uutisia juuri nyt.</p></section>"

    rows = ""
    for item in items:
        summary_html = (
            f"<div class='summary'>{html.escape(item['summary'])}</div>"
            if item.get("summary")
            else ""
        )
        rows += f"""
        <li class="news-item">
          <a href="{html.escape(item['link'])}" target="_blank" rel="noopener">{html.escape(item['title'])}</a>
          {summary_html}
          <div class="meta">{html.escape(item['source'])}</div>
        </li>"""

    return f"""
    <section>
      <h2>{title}</h2>
      <ul class="news-list">{rows}
      </ul>
    </section>"""


def render_opetus(opetus):
    if not opetus or not opetus.get("title"):
        return ""
    return f"""
    <div class="opetus">
      <div class="opetus-label">💡 Päivän opetuspätkä</div>
      <div class="opetus-title">{html.escape(opetus['title'])}</div>
      <div class="opetus-text">{html.escape(opetus.get('explanation', ''))}</div>
    </div>"""


def main():
    ai_items, opetus = get_section_items(AI_FEEDS, AI_INSTRUCTIONS, include_opetus=True)
    nhl_items, _ = get_section_items(NHL_FEEDS, NHL_INSTRUCTIONS)
    updated = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")

    page = f"""<!DOCTYPE html>
<html lang="fi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Päivän uutiset</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", Roboto, sans-serif; max-width: 700px;
         margin: 0 auto; padding: 24px 16px; background: #fafafa; color: #1a1a1a; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 4px; }}
  .updated {{ color: #888; font-size: 0.85rem; margin-bottom: 32px; }}
  h2 {{ font-size: 1.1rem; border-bottom: 2px solid #ddd; padding-bottom: 6px; }}
  .news-list {{ list-style: none; padding: 0; margin: 0; }}
  .news-item {{ padding: 12px 0; border-bottom: 1px solid #eee; }}
  .news-item a {{ font-weight: 600; color: #1a1a1a; text-decoration: none; }}
  .news-item a:hover {{ text-decoration: underline; }}
  .summary {{ font-size: 0.9rem; color: #444; margin-top: 4px; line-height: 1.4; }}
  .meta {{ font-size: 0.8rem; color: #999; margin-top: 4px; }}
  section {{ margin-bottom: 40px; }}
  .empty {{ color: #999; font-style: italic; }}
  .opetus {{ background: #fff7e6; border: 1px solid #f0dca0; border-radius: 8px;
            padding: 16px; margin-bottom: 32px; }}
  .opetus-label {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.03em;
                   color: #a67c00; font-weight: 600; margin-bottom: 6px; }}
  .opetus-title {{ font-weight: 600; margin-bottom: 6px; }}
  .opetus-text {{ font-size: 0.9rem; color: #444; line-height: 1.5; }}
</style>
</head>
<body>
  <h1>Päivän uutiset</h1>
  <div class="updated">Päivitetty: {updated}</div>
  {render_section("🤖 AI-uutiset", ai_items)}
  {render_opetus(opetus)}
  {render_section("🏒 NHL-uutiset", nhl_items)}
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(page)

    print(f"index.html luotu. AI-uutisia: {len(ai_items)}, NHL-uutisia: {len(nhl_items)}")


if __name__ == "__main__":
    main()
