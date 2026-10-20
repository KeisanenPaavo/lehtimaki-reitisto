-- Valkealammen reittikartta: kuntoilmoitukset, kommentit ja kuvat ilman kirjautumista.
-- Anonyymi käyttäjä (anon) voi lukea näkyvät rivit ja lisätä uusia, ei muokata eikä poistaa.
-- Moderointi: omistaja muuttaa status-kenttää Supabasen hallinnasta (service role).

create schema if not exists private;
revoke all on schema private from public;

-- ---------- kohteet ----------
create table public.targets (
  id        text primary key check (id ~ '^[a-z0-9-]{3,60}$'),
  kind      text not null check (kind in ('route', 'shelter')),
  name      text not null,
  lipas_id  integer,
  osm_ids   text[] not null default '{}',
  lat       double precision,
  lon       double precision
);

-- ---------- yhteiset tarkistukset ----------
-- Sallitut pikatagit (reitit ja taukopaikat)
create function private.allowed_tags() returns text[]
language sql immutable as $$
  select array[
    'ajettu', 'pohja-hyva', 'jainen', 'upottava', 'lumeton',
    'kaatunut-puu', 'vesilammikko', 'mutainen',
    'puita-on', 'puut-loppu', 'siisti', 'roskia', 'vaurio'
  ]::text[]
$$;

-- ---------- kuntoilmoitukset ----------
create table public.reports (
  id          uuid primary key default gen_random_uuid(),
  target_id   text not null references public.targets(id),
  condition   text check (condition in ('hyva', 'kelvollinen', 'huono', 'suljettu')),
  tags        text[] not null default '{}' check (tags <@ private.allowed_tags() and cardinality(tags) <= 6),
  note        text check (char_length(note) <= 500),
  created_at  timestamptz not null default now(),
  status      text not null default 'visible' check (status in ('visible', 'hidden')),
  check (condition is not null or cardinality(tags) > 0 or note is not null)
);
create index reports_target_created on public.reports (target_id, created_at desc);

-- ---------- kommentit ----------
create table public.comments (
  id           uuid primary key default gen_random_uuid(),
  target_id    text not null references public.targets(id),
  author_name  text check (char_length(author_name) between 1 and 40),
  body         text not null check (char_length(btrim(body)) between 1 and 1000),
  created_at   timestamptz not null default now(),
  status       text not null default 'visible' check (status in ('visible', 'hidden'))
);
create index comments_target_created on public.comments (target_id, created_at desc);

-- ---------- kuvat ----------
create table public.photos (
  id            uuid primary key default gen_random_uuid(),
  target_id     text not null references public.targets(id),
  storage_path  text not null unique
                check (storage_path ~ '^pending/[0-9a-f-]{36}\.(jpg|png|webp)$'),
  caption       text check (char_length(caption) <= 200),
  author_name   text check (char_length(author_name) between 1 and 40),
  created_at    timestamptz not null default now(),
  status        text not null default 'pending' check (status in ('pending', 'approved', 'rejected'))
);
create index photos_target_created on public.photos (target_id, created_at desc);

-- ---------- nopeusrajoitus ----------
-- IP-osoitteesta tallennetaan vain suolattu tiiviste, ja vanhat rivit poistetaan.
create table private.settings (
  key   text primary key,
  value text not null
);
insert into private.settings values ('ip_salt', encode(extensions.gen_random_bytes(32), 'hex'));

create table private.rate_events (
  id       bigint generated always as identity primary key,
  ip_hash  text,
  tbl      text not null,
  at       timestamptz not null default now()
);
create index rate_events_at on private.rate_events (at);
create index rate_events_ip_at on private.rate_events (ip_hash, at);

create function private.enforce_rate_limit() returns trigger
language plpgsql security definer set search_path = '' as $$
declare
  hdrs   json := nullif(current_setting('request.headers', true), '')::json;
  ip     text := btrim(split_part(coalesce(hdrs ->> 'x-forwarded-for', hdrs ->> 'x-real-ip', ''), ',', 1));
  h      text;
  n_ip   integer;
  n_all  integer;
begin
  -- Ylläpito (service role / SQL) ei ole rajoitettu
  if current_user not in ('anon', 'authenticated') then
    return new;
  end if;

  delete from private.rate_events where at < now() - interval '1 day';

  if ip <> '' then
    select encode(extensions.digest(ip || (select value from private.settings where key = 'ip_salt'), 'sha256'), 'hex') into h;
    select count(*) into n_ip from private.rate_events
      where ip_hash = h and at > now() - interval '10 minutes';
    if n_ip >= 10 then
      raise exception 'Liian monta lähetystä lyhyessä ajassa. Yritä hetken päästä uudelleen.'
        using errcode = 'P0001';
    end if;
  end if;

  select count(*) into n_all from private.rate_events where at > now() - interval '1 hour';
  if n_all >= 300 then
    raise exception 'Palvelu on tilapäisesti ruuhkautunut. Yritä myöhemmin uudelleen.'
      using errcode = 'P0001';
  end if;

  insert into private.rate_events (ip_hash, tbl) values (h, tg_table_name);
  return new;
end $$;

create trigger reports_rate_limit  before insert on public.reports  for each row execute function private.enforce_rate_limit();
create trigger comments_rate_limit before insert on public.comments for each row execute function private.enforce_rate_limit();
create trigger photos_rate_limit   before insert on public.photos   for each row execute function private.enforce_rate_limit();

-- Kuvarivi saa viitata vain jo ladattuun tiedostoon
create function private.photo_object_exists(p text) returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from storage.objects where bucket_id = 'photos' and name = p)
$$;

-- Tiedoston saa lukea vain, jos kuva on hyväksytty
create function private.photo_is_approved(p text) returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.photos where storage_path = p and status = 'approved')
$$;

grant usage on schema private to anon, authenticated;
revoke all on all functions in schema private from public;
grant execute on function private.allowed_tags(), private.photo_object_exists(text), private.photo_is_approved(text)
  to anon, authenticated;

-- ---------- oikeudet: vain tarvittavat sarakkeet ----------
revoke all on public.targets, public.reports, public.comments, public.photos from anon, authenticated;

grant select on public.targets to anon, authenticated;
grant select (id, target_id, condition, tags, note, created_at)          on public.reports  to anon, authenticated;
grant insert (target_id, condition, tags, note)                          on public.reports  to anon, authenticated;
grant select (id, target_id, author_name, body, created_at)              on public.comments to anon, authenticated;
grant insert (target_id, author_name, body)                              on public.comments to anon, authenticated;
grant select (id, target_id, storage_path, caption, author_name, created_at) on public.photos to anon, authenticated;
grant insert (target_id, storage_path, caption, author_name)            on public.photos   to anon, authenticated;

-- ---------- RLS ----------
alter table public.targets  enable row level security;
alter table public.reports  enable row level security;
alter table public.comments enable row level security;
alter table public.photos   enable row level security;

create policy "targets: kaikki lukevat" on public.targets
  for select to anon, authenticated using (true);

create policy "reports: näkyvät luettavissa" on public.reports
  for select to anon, authenticated using (status = 'visible');
create policy "reports: kuka tahansa lisää" on public.reports
  for insert to anon, authenticated with check (status = 'visible');

create policy "comments: näkyvät luettavissa" on public.comments
  for select to anon, authenticated using (status = 'visible');
create policy "comments: kuka tahansa lisää" on public.comments
  for insert to anon, authenticated with check (status = 'visible');

create policy "photos: hyväksytyt luettavissa" on public.photos
  for select to anon, authenticated using (status = 'approved');
create policy "photos: kuka tahansa lisää odottamaan" on public.photos
  for insert to anon, authenticated
  with check (status = 'pending' and private.photo_object_exists(storage_path));
