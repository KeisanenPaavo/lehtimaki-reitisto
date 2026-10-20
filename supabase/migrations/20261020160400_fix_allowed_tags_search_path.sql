-- Security advisor 0011: kiinteä search_path myös allowed_tags-funktiolle.
alter function private.allowed_tags() set search_path = '';
