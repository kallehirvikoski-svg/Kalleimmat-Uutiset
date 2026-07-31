# Päivän uutiset -sivusto

Ilmainen, automaattisesti päivittyvä sivu AI- ja NHL-uutisille. Toimii GitHubin
ilmaisilla työkaluilla (GitHub Actions + GitHub Pages) — ei kuukausimaksuja.

## Käyttöönotto

1. **Luo uusi julkinen GitHub-repo**, esim. nimellä `omat-uutiset`.
2. 2. **Lataa nämä tiedostot** samaan kansiorakenteeseen repoon:
   3.    - `scripts/generate_site.py`
         -    - `.github/workflows/update.yml`
              -    - `requirements.txt`
                   - 3. **Hanki Anthropic API-avain:**
                     4.    Mene osoitteeseen console.anthropic.com → luo API-avain (tarvitset Anthropic-tilin
                     5.   ja pienen saldon tilille — tämä on ainoa maksullinen osa koko ratkaisua).
                     6.   4. **Lisää avain repon secretiksi:**
                          5.    Repo → Settings → Secrets and variables → Actions → "New repository secret" →
                          6.   nimeksi ANTHROPIC_API_KEY, arvoksi kopioimasi avain → Add secret.
                          7.   5. **Salli Actionsin kirjoittaa repoon:**
                               6.    Repo → Settings → Actions → General → kohta "Workflow permissions" →
                               7.   valitse "Read and write permissions" → Save.
                               8.   6. **Ota GitHub Pages käyttöön:**
                                    7.    Repo → Settings → Pages → Source: "Deploy from a branch" →
                                    8.   Branch: main, kansio: / (root) → Save.
                                    9.   7. **Aja työnkulku kerran manuaalisesti**, jotta index.html syntyy heti:
                                         8.    Repo → Actions-välilehti → valitse "Päivitä uutissivu" → "Run workflow".
                                         9.8. Muutaman minuutin kuluttua sivu löytyy osoitteesta:
                                              https://KÄYTTÄJÄNIMESI.github.io/REPON-NIMI/

                                           Tästä eteenpäin sivu päivittyy itsestään joka aamu (klo 6 UTC / n. 8-9 Suomen aikaa),
                                         ja jokaisella ajolla Claude valitsee 5 parasta uutista per aihe, kirjoittaa niille
                                         suomenkieliset yhteenvedot ja priorisoi ne alkuperäisten kriteerien mukaan (AI:
                                         uudet mallit, automaatio, pk-yritys/tuotantosovellukset; NHL: tulokset, siirrot,
                                         loukkaantumiset).

                                         ## Uutislähteiden muokkaaminen

                                         RSS-lähteet ovat listattuina scripts/generate_site.py-tiedoston alussa
                                         (AI_FEEDS ja NHL_FEEDS). Voit lisätä, poistaa tai vaihtaa niitä vapaasti —
                                         mikä tahansa RSS/Atom-feed käy.

                                         ## Huomioitavaa

                                         - Osa uutissivustoista voi joskus muuttaa tai poistaa RSS-feedinsä. Jos jokin
                                         -   lähde lakkaa toimimasta, skripti jättää sen vain huomiotta eikä kaadu — mutta
                                         -     kannattaa silloin päivittää lista tuoreemmalla feedillä.
                                         - - Skripti käyttää Claude Haikua (halvin ja nopein malli), ja ajaa sen kerran
                                           -   päivässä kahdelle lyhyelle promptille (AI + NHL). Kustannus tällä
                                           -     käyttömäärällä on hyvin pieni, mutta kannattaa tarkistaa ajantasainen
                                           -   hinnoittelu Anthropicin sivuilta ja seurata käyttöä console.anthropic.com:ssa.
                                           -   - Jos ANTHROPIC_API_KEY-secret puuttuu tai API-kutsu epäonnistuu jostain
                                               -   syystä, sivu näyttää silti raa'at otsikot ja linkit varasuunnitelmana —
                                               -     ajo ei koskaan kaadu kokonaan tämän takia.
