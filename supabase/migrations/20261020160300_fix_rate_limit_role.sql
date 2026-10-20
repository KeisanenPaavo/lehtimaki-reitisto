-- Korjaus: security definer -funktiossa current_user on funktion omistaja, ei anon.
-- Rajoitus koskee nyt kaikkia API-pyyntöjä (request.headers asetettu) paitsi service rolea.
-- Suorat SQL-ajot (hallinta, migraatiot) ohittavat rajoituksen.

create or replace function private.enforce_rate_limit() returns trigger
language plpgsql security definer set search_path = '' as $$
declare
  hdrs   json := nullif(current_setting('request.headers', true), '')::json;
  claims json := nullif(current_setting('request.jwt.claims', true), '')::json;
  ip     text;
  h      text;
  n_ip   integer;
  n_all  integer;
begin
  if hdrs is null or coalesce(claims ->> 'role', '') = 'service_role' then
    return new;
  end if;

  delete from private.rate_events where at < now() - interval '1 day';

  ip := btrim(split_part(coalesce(hdrs ->> 'x-forwarded-for', hdrs ->> 'x-real-ip', hdrs ->> 'cf-connecting-ip', ''), ',', 1));
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
