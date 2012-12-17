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
  playlist_id integer primary key autoincrement,
  twitter_id integer not null,
  playlist_name string not null
);

drop table if exists playlistsongs;
create table playlistsongs (
  playlist_id integer not null,
  song_id integer not null,
  rank integer not null
);

drop table if exists songs;
create table songs (
  song_id integer primary key autoincrement,
  song_title string not null,
  song_artist string not null,
  song_album string not null,
  twitter_id integer not null
);

drop table if exists songmap;
create table songmap (
  song_id integer primary key,
  celeblime_id string not null,
  twitter_id integer not null
);

drop table if exists playlistmap;
create table playlistmap (
  playlist_id integer primary key,
  celeblime_id string not null,
  twitter_id integer not null
);