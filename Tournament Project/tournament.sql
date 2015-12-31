-- Table definitions for the tournament project.
--
-- Put your SQL 'create table' statements in this file; also 'create view'
-- statements if you choose to use it.
--
-- You can write comments in this file by starting them with two dAShes, like
-- these lines here.

-- connect to tournament DB
\c tournament

-- create new instance of tournament table. note: must be disconnected
DROP DATABASE IF EXISTS tournament;
CREATE DATABASE tournament;

-- create new instance of players table
DROP TABLE IF EXISTS players;
CREATE TABLE players (id serial primary key, name text);

-- create new instance of matches table
DROP TABLE IF EXISTS matches;
CREATE TABLE matches (id serial, winner int references players (id), loser int references players (id));

-- create view to join players with matches
CREATE VIEW JoinAll AS SELECT players.id AS Player, matches.id AS Match, matches.winner AS Winner, matches.loser AS Loser FROM players, matches WHERE players.id = winner or players.id = loser;

-- create view to display win count for each player
CREATE VIEW Winners AS SELECT player, name, count(winner) AS wins FROM JoinAll WHERE player = winner GROUP BY player;

-- create view to display loss count for each player
CREATE VIEW Losers AS SELECT player, count(loser) AS losses FROM JoinAll WHERE player = loser GROUP BY player;

-- create view to show match count for each player
CREATE VIEW SumMatches AS SELECT player, count(*) AS matches FROM JoinAll GROUP BY player;

-- create view to join win and loss count in one table
CREATE VIEW Standings AS SELECT winners.player,
           winners.wins,
           losers.losses 
      FROM winners
 LEFT JOIN losers ON losers.player = winners.player
UNION
    SELECT losers.player,
           winners.wins,
           losers.losses
      FROM winners
RIGHT JOIN losers ON losers.player = winners.player ORDER BY wins DESC nulls last;

-- create view to add matches count to standings
CREATE VIEW StandingsWithMatches AS select players.id, players.name, Standings.wins, summatches.matches from Standings, summatches, players where Standings.player = summatches.player and players.id = summatches.player ORDER BY wins DESC nulls last;

-- create final view to see player & id if no matches, and display wins & matches as 0 if null
CREATE VIEW PlayerStandings AS SELECT players.id, players.name, coalesce(StandingsWithMatches.wins, 0) as wins, coalesce(StandingsWithMatches.matches, 0) as matches
      FROM players
 LEFT JOIN StandingsWithMatches ON StandingsWithMatches.id = players.id;



