drop table if exists users;
create table users (
  twitter_id integer primary key,
  token string not null,
  secret string not null,
  screen_name string not null,
  name string not null,
  logins integer not null
);

drop table if exists playlists;
create table playlists (
  id integer primary key autoincrement,
  playlist_id string not null,
  twitter_id integer not null,
  playlist_name string not null
  visibility boolean not null
);

drop table if exists playlistsongs;
create table playlistsongs (
  playlist_id string not null,
  song_id integer not null,
  rank integer not null,
);

drop table if exists played;
create table played (
  twitter_id integer not null,
  song_id integer not null,
  played_at integer not null,
  played_count integer not null,
  visibility boolean not null
);

drop table if exists songs;
create table songs (
  id integer primary key autoincrement,
  song_id string not null,
  song_title string not null,
  song_artist string not null,
  song_album string not null,
  song_duration integer not null,
  twitter_id integer not null
);
