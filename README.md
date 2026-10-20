# Lehtimäen reitistö

Karttapalvelu Valkealammen ulkoilualueen (Lehtimäki, Alajärvi) reiteistä, laduista ja taukopaikoista. Kaikki reittidata on avointa: LIPAS (JYU, CC BY 4.0) ja © OpenStreetMap -tekijät (ODbL).

- Kartta ja data: [`valkealampi/`](valkealampi/), jonka kuvaus on tiedostossa [valkealampi/README.md](valkealampi/README.md)
- Julkaisu: GitHub Pages. Jokainen push `main`-haaraan julkaisee tiedostot `valkealampi/index.html` ja `valkealampi/data/` ([.github/workflows/pages.yml](.github/workflows/pages.yml)).
- Datan päivitys: `cd valkealampi && python3 build.py`, sitten commit ja push.

API-avaimia (esim. MML) ei tallenneta repoon.
