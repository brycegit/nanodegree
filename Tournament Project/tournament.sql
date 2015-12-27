-- Table definitions for the tournament project.
--
-- Put your SQL 'create table' statements in this file; also 'create view'
-- statements if you choose to use it.
--
-- You can write comments in this file by starting them with two dashes, like
-- these lines here.

-- create new instance of tournament table. note: must be disconnected
DROP DATABASE IF EXISTS tournament;
CREATE DATABASE tournament;

-- create new instance of players table
DROP TABLE IF EXISTS players;
CREATE TABLE players (id serial primary key, name text, wins int, matches int);

-- create new instance of matches table
DROP TABLE IF EXISTS matches;
CREATE TABLE matches (id serial, winner int references players (id), loser int references players (id));