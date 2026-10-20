-- Kuvien tallennus: yksityinen bucket. Kuka tahansa voi ladata kuvan pending/-kansioon
-- (enintään 5 Mt, jpg/png/webp). Tiedoston saa luettua (signed URL) vasta, kun
-- vastaava photos-rivi on hyväksytty. Päällekirjoitus ja poisto eivät ole sallittuja.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('photos', 'photos', false, 5242880, array['image/jpeg', 'image/png', 'image/webp'])
on conflict (id) do update
  set public = excluded.public,
      file_size_limit = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;

create policy "photos: anonyymi lataus odottamaan" on storage.objects
  for insert to anon, authenticated
  with check (
    bucket_id = 'photos'
    and name ~ '^pending/[0-9a-f-]{36}\.(jpg|png|webp)$'
  );

create policy "photos: hyväksytyt luettavissa" on storage.objects
  for select to anon, authenticated
  using (bucket_id = 'photos' and private.photo_is_approved(name));
