# Valkealammen reittikartta

Kartta Valkealammen ulkoilualueen (Lehtimäki, Alajärvi) laduista, poluista ja muista reiteistä. Kaikki viivat ovat avoimesta datasta, eikä mitään ole piirretty käsin.

- **Kartta:** `index.html`. Yksi tiedosto, jossa data on upotettuna. Se aukeaa suoraan selaimessa ilman palvelinta (Leaflet ja taustakartat tulevat verkosta).
- **Taustakartat** (tasonvalitsin oikeassa yläkulmassa): OpenStreetMap (oletus), OpenTopoMap (maasto ja korkeuskäyrät), Esri-ilmakuva ja CyclOSM (polut ja pyöräilyreitit korostettuina). Kaikki toimivat ilman avainta. MML:n maastokartta tulee valikkoon vain, jos osoitteeseen lisätään `?mmlkey=OMA_AVAIN`. Kapsin MML-karttatiilet (tiles.kartat.kapsi.fi) testattiin myös, mutta ne eivät vastanneet 2026-10-20.
- **Data:** `data/lipas.geojson`, `data/osm.geojson`, `data/laavut.geojson` (laavut ja kodat, molemmat lähteet) ja `data/_stats.json` (tilastot ja vertailu).
- **Kunto, kommentit ja kuvat:** reitin tai taukopaikan popupissa on painike, joka avaa kohdekortin. Kortissa voi ilmoittaa kunnon, kommentoida ja lähettää kuvan ilman kirjautumista. Tiedot tallentuvat Supabaseen (ks. [../supabase/README.md](../supabase/README.md)). Viimeisin kuntoilmoitus värittää reitin: ladulla ilmoitus on voimassa 48 h, muilla reiteillä 7 pv.
- **Kohdelinkit** (esim. QR-koodeihin): `index.html#jakalamaen-kota`, `#valaistu-latu` jne. Tunnisteet ovat taulussa `targets`.
- **Pelkkä uudelleenrakennus** pohjan muokkauksen jälkeen ilman verkkohakuja: `python3 build.py --render`.
- **Uudelleenhaku:** `python3 build.py`. Jos jokin lähde ei vastaa, käytetään edellistä tallennettua tiedostoa. Skripti käyttää vain Pythonin standardikirjastoa ja `curl`ia. Se hakee datan ja rakentaa `index.html`:n pohjasta `template.html`.

## Haku

Haettu **2026-10-20 klo 07:26 (UTC+3)**.

| Vaihe | Tulos |
|---|---|
| Geokoodaus (Nominatim) `Valkealammentie 200, 63510 Alajärvi` | Valkealammen hiihto- ja matkailukeskus, **62.775183, 23.865097** |
| Rajaus ±3 km (EPSG:4326, W,S,E,N) | **23.806189, 62.748234, 23.924004, 62.802133** |
| Valkealampi (OSM `natural=water`, 62.77684, 23.87021) rajauksessa? | Kyllä, joten keskipistettä ei siirretty |

### 1. LIPAS
- `GetCapabilities` osoitteesta `https://lipas.fi/geoserver/lipas/ows`. Tasoksi valittiin **`lipas:lipas_kaikki_reitit`**, jossa ovat kaikki reittityypit viivageometrioina. Tyyppikohtaiset tasot (`lipas_4401_kuntorata`, `lipas_4402_latu` …) ovat myös olemassa.
- `GetFeature` (`outputFormat=application/json`, `srsName=EPSG:4326`, bbox). WFS 1.1.0 palautti 0 kohdetta akselijärjestyksen takia. Versiolla 1.0.0 (lon,lat) haku toimi ja palautti **45 reittiosaa, 7 liikuntapaikkaa**.
- WFS:n koordinaatit on pyöristetty 4 desimaaliin (noin 5–11 m), eikä tasolla ole valaistus- tai pituustietoa. Siksi jokaisen löytyneen liikuntapaikan täysi geometria ja ominaisuudet haettiin LIPAS-rajapinnasta `https://api.lipas.fi/v2/sports-sites/{id}`. Tämä on `lipas.fi/rest`:n nykyinen versio.
- Kaksi paikkaa osui WFS-hakuun vain rajauslaatikkonsa (envelope) perusteella, eikä niillä ole viivaa rajauksen sisällä: *EuroVelo 10* (4412) ja *Alajärven lenkki* (4422). Ne eivät näy kartalla.
- Lähdedatassa paikan 509835 osat 13, 14 ja 16 ovat identtisiä kopioita muista osista (yhteensä 3,3 km). Ne poistettiin. Poiston jälkeen laskettu pituus (8,48 km) vastaa LIPASin ilmoittamaa 8,5 km:ä.
- Tyyppikoodit ja -nimet otettiin datan omista kentistä (`tyyppikoodi`, `tyyppi_nimi_fi`).

### 2. OpenStreetMap
- Overpass `https://overpass-api.de/api/interpreter` tehtävänannon kyselyllä (kysely tallessa `osm.geojson`-tiedoston `metadata.query`-kentässä).
- Kysely palautti **202 elementtiä**: 202 viivaa ja **0 reittirelaatiota**. Muunnos GeoJSONiksi tehtiin omalla koodilla (`build.py`).
- Luokittelu: `piste:type=nordic` → latu (vaikka viiva olisi myös `highway=track`), `path`/`footway`/`cycleway`/`bridleway` → polku ja `track` → ajoura.

### 3. Maanmittauslaitos
**Ei haettu**, koska API-avainta ei ole annettu. `mml.geojson` puuttuu. MML:n maastokartan voi kuitenkin ottaa taustaksi omassa selaimessa ilman, että avain tallentuu tiedostoon: `index.html?mmlkey=OMA_AVAIN`.

Kaikki viivat on leikattu hakurajaukseen. Pituudet on laskettu isoympyräkaavalla (haversine) leikatuista viivoista.

## Kohteet ja pituudet

| Lähde | Tyyppi | Kohteita | Pituus rajauksessa |
|---|---|---:|---:|
| LIPAS | 4402 Hiihtolatu | 27 osaa / 2 latua | 13,79 km |
| | ↳ Valkealammen valaistu latu (509834) | 11 | 5,31 km (LIPAS: 5,4 km, valaistu 5,4 km) |
| | ↳ Valkealammen valaisemattomat ladut (509835) | 16 | 8,48 km (LIPAS: 8,5 km) |
| LIPAS | 4401 Kuntorata, Valkealammen valaistu kuntorata (95942) | 11 osaa / 1 | 5,31 km (LIPAS: 5,4 km, valaistu 5,4 km) |
| LIPAS | 4422 Moottorikelkkaura | 2 osaa / 2 uraa | 14,93 km (LIPAS kokonaan: 14,94 + 16,48 km) |
| **LIPAS yhteensä** | | **40 kohdetta (5 liikuntapaikkaa)** | **34,03 km** |
| OSM | latu (`piste:type=nordic`) | 10 | 4,49 km |
| OSM | polku (`path`) | 70 | 23,28 km |
| OSM | polku (`footway`) | 5 | 0,35 km |
| OSM | polku (`cycleway`) | 1 | 0,13 km |
| OSM | ajoura (`track`) | 116 | 51,24 km |
| OSM | reittirelaatiot | 0 | 0 km |
| **OSM yhteensä** | | **202** | **79,49 km** |
| MML | – | ei haettu | – |

Valaistu latu ja kuntorata ovat LIPASissa samaa geometriaa, joten ne ovat kartalla päällekkäin (punainen sinisen päällä).

## LIPAS vs. OSM (30 m toleranssi)

- **Suurin osa LIPAS-laduista ei ole OSM:ssä latuna.** OSM:n `piste:type=nordic` kattaa 5,44 km LIPASin 13,79 km:stä. Valaistusta ladusta katettuna on 2,93 / 5,31 km ja valaisemattomista 2,51 / 8,48 km.
- Ero on kuitenkin lähes kokonaan tagauksessa eikä geometriassa: 13,07 km LIPAS-laduista kulkee jonkin OSM-viivan päällä. Nämä OSM-viivat ovat enimmäkseen `track` (~6,3 km) ja `path` (~1,5 km), joilta latutagi puuttuu.
- **Vain LIPASissa** (ei mitään OSM-viivaa 30 m:n sisällä, yhteensä noin 0,7 km): valaisemattomien latujen pätkät kohdissa 62.7648, 23.8423 (noin 250 m, länsilenkki) ja 62.7609, 23.8598 (noin 290 m, eteläosa) sekä valaistun ladun noin 70 m kohdassa 62.7707, 23.8624.
- **Vain OSM:ssä latuna:** way/1086607064, josta noin 400 m kulkee yli 30 m:n päässä LIPAS-ladusta kohdassa 62.7594, 23.8593. Tämä on todennäköisesti sama eteläinen lenkki kuin yllä, eri tavalla piirrettynä.
- Moottorikelkkaurat ovat vain LIPASissa. OSM-kyselyyn ei sisältynyt `snowmobile`-tageja, joten niiden puuttumista OSM:stä ei tarkistettu.
- OSM:ssä on noin 75 km polkuja ja ajouria, joita LIPAS ei kuvaa. Tämä on odotettavaa, koska LIPAS sisältää vain hoidetut reitit.

## Laavut ja kodat

Haetut lähteet: LIPAS-taso `lipas:lipas_301_laavu_kota_kammi` (lisätiedot `api.lipas.fi/v2`:sta) sekä OSM `amenity=shelter` ja `tourism=wilderness_hut`. Tasot `lipas_302_tupa`, `lipas_304_ulkoilumaja_hiihtomaja` ja `lipas_206_ruoanlaittopaikka` tarkistettiin myös, eikä rajauksesta löytynyt niistä kohteita. Tyyppi on päätelty nimestä (kota/laavu) tai OSM:n `shelter_type`-tagista.

| Paikka | Tyyppi | Sijainti (lat, lon) | LIPAS | OSM |
|---|---|---|---|---|
| Jäkälämäen kota | kota | 62.76186, 23.84352 | 605374 (WC, vapaa käyttö, opastus 2,3 km Valkealammen kautta) | node/12105990404 |
| Jäkälämäen laavu | laavu | 62.76189, 23.84316 | – | node/12105990482 |
| "Kota", eteläinen kuntoratalenkki | kota/laavu? | 62.76350, 23.86306 | – | way/190921915 (`building=hut`, `fireplace=yes`, mutta myös `shelter_type=lean_to`) |
| Laavu, keskuksen eteläpuoli | laavu | 62.77515, 23.86257 | – | node/8401787171 |
| Laavu, keskus | laavu | 62.77574, 23.86360 | – | node/5357269982 |
| Laavu, rannalla | laavu | 62.77632, 23.86699 | – | node/2026462596 |
| Katos, rannalla (tyyppi puuttuu) | katos | 62.77673, 23.86682 | – | node/8401787170 |

LIPAS tuntee alueelta vain Jäkälämäen kodan. Muut 6 katosta löytyvät vain OSM:stä. Valkealammen keskuksen laavuilla on OSM:ssä tagi `snowmobile=yes`. Jäkälämäen kodan sijainti on LIPASissa ja OSM:ssä sama (noin 1 m:n tarkkuudella).

## Lisenssit
- LIPAS, Jyväskylän yliopisto: CC BY 4.0
- © OpenStreetMap -tekijät: ODbL
- OpenTopoMap: CC BY-SA (OSM-data ja SRTM-korkeusmalli)
- CyclOSM: OSM-data, tyyli © CyclOSM
- Esri World Imagery: © Esri, Maxar, Earthstar Geographics (Esrin käyttöehdot)
- © Maanmittauslaitos: CC BY 4.0 (vain jos maastokartta otetaan käyttöön avaimella)
