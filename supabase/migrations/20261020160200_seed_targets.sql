-- Kohteet, joihin voi jättää ilmoituksia, kommentteja ja kuvia.
-- Lähde: valkealampi/data/lipas.geojson ja laavut.geojson (haettu 2026-10-20).
insert into public.targets (id, kind, name, lipas_id, osm_ids, lat, lon) values
  ('valaistu-latu', 'route', 'Valkealammen valaistu latu', 509834, array[]::text[], 62.769564, 23.863986),
  ('valaisemattomat-ladut', 'route', 'Valkealammen valaisemattomat ladut', 509835, array[]::text[], 62.766221, 23.858900),
  ('kuntorata', 'route', 'Valkealammen valaistu kuntorata', 95942, array[]::text[], 62.769564, 23.863986),
  ('kelkkaura-valkealampi', 'route', 'Valkealammen moottorikelkkaura', 606958, array[]::text[], 62.783926, 23.861362),
  ('kelkkaura-kirkonkyla', 'route', 'Valkealampi-Kirkonkylä moottorikelkkaura', 606959, array[]::text[], 62.791721, 23.880660),
  ('laavu-ranta', 'shelter', 'Laavu, uimaranta', null, array['node/2026462596']::text[], 62.776322, 23.866989),
  ('laavu-keskus', 'shelter', 'Laavu, keskus', null, array['node/5357269982']::text[], 62.775737, 23.863599),
  ('katos-ranta', 'shelter', 'Katos, uimaranta', null, array['node/8401787170']::text[], 62.776728, 23.866817),
  ('laavu-keskus-etela', 'shelter', 'Laavu, keskuksen eteläpuoli', null, array['node/8401787171']::text[], 62.775147, 23.862569),
  ('jakalamaen-kota', 'shelter', 'Jäkälämäen kota', 605374, array['node/12105990404']::text[], 62.761847, 23.843495),
  ('jakalamaen-laavu', 'shelter', 'Jäkälämäen laavu', null, array['node/12105990482']::text[], 62.761886, 23.843163),
  ('etelalenkin-kota', 'shelter', 'Kota (eteläinen kuntoratalenkki)', null, array['way/190921915']::text[], 62.763500, 23.863061)
on conflict (id) do update set name = excluded.name, lipas_id = excluded.lipas_id, osm_ids = excluded.osm_ids, lat = excluded.lat, lon = excluded.lon;
