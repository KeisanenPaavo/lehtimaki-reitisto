# Supabase: kuntoilmoitukset, kommentit ja kuvat

Projekti: **lehtimaki-reitisto** (`jflqdwbelfqwudhlyxxh`, eu-north-1)
API: `https://jflqdwbelfqwudhlyxxh.supabase.co`
Julkinen avain (saa olla selaimessa): `sb_publishable_KdOOksTSl9fbi5wlzPdrhw_m5Om-1iI`

Tietokanta luodaan tiedostoista `migrations/`, aikajärjestyksessä.

## Mitä kävijä voi tehdä ilman kirjautumista

| Taulu | Lukea | Lisätä | Muokata / poistaa |
|---|---|---|---|
| `targets` (12 kohdetta: 5 reittiä, 7 taukopaikkaa) | kaikki | – | – |
| `reports` (kunto: `hyva`/`kelvollinen`/`huono`/`suljettu`, pikatagit, muistiinpano ≤ 500 merkkiä) | näkyvät | kyllä, näkyy heti | ei |
| `comments` (nimimerkki ≤ 40 merkkiä, teksti ≤ 1000 merkkiä) | näkyvät | kyllä, näkyy heti | ei |
| `photos` (kuvateksti ≤ 200 merkkiä) | hyväksytyt | kyllä, odottaa hyväksyntää | ei |

- **Status-kenttä** on kävijältä piilossa, eikä kävijä voi asettaa sitä.
- **Nopeusrajoitus:** 10 lähetystä 10 minuutissa samasta IP-osoitteesta, ja koko palvelussa enintään 300 lähetystä tunnissa. IP-osoitteesta tallennetaan vain suolattu tiiviste yksityiseen tauluun, ja yli vuorokauden vanhat rivit poistetaan.
- **Pikatagit:** `ajettu`, `pohja-hyva`, `jainen`, `upottava`, `lumeton`, `kaatunut-puu`, `vesilammikko`, `mutainen`, `puita-on`, `puut-loppu`, `siisti`, `roskia`, `vaurio`.

## Kuvan lähetys (selaimesta)

1. Poista sijaintitiedot (EXIF), esimerkiksi piirtämällä kuva canvasille ja tallentamalla se uudelleen JPEG:ksi.
2. Lataa tiedosto bucketiin `photos` polkuun `pending/<uuid>.jpg`. Sallittuja ovat jpg, png ja webp, enintään 5 Mt. Päällekirjoitus ei ole sallittu.
3. Lisää `photos`-rivi, jossa `storage_path = 'pending/<uuid>.jpg'`. Käytä otsaketta `Prefer: return=minimal`, koska odottava rivi ei ole kävijälle luettavissa.
4. Hyväksytyn kuvan tiedostolle tehdään selaimessa allekirjoitettu osoite (`createSignedUrl`).

**Huom:** pyydä aina sarakkeet nimeltä (`select=id,target_id,body,...`). `select=*` epäonnistuu, koska status-sarake ei ole luettavissa.

## Moderointi (Supabasen hallinta → Table Editor)

- **Kuva:** `photos`-rivin `status` muutetaan arvoon `approved` tai `rejected`. Odottavat kuvat näkyvät suodattimella `status = pending`.
- **Kommentin tai ilmoituksen piilotus:** `status` muutetaan arvoon `hidden`.
- **Hylätyn kuvan tiedoston poisto:** Storage → `photos` → `pending/`.

Vielä puuttuu: botintorjunta (esim. Cloudflare Turnstile Edge Functionin kautta), asiattomuusilmoitus-nappi ja oma ylläpitosivu.
