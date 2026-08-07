const fs = require('fs/promises');

const headers = {
  'User-Agent': 'Mozilla/5.0',
  Referer: 'https://www.nba.com/',
  Origin: 'https://www.nba.com',
};

const gameLogFields = [
  'SEASON_YEAR', 'PLAYER_ID', 'PLAYER_NAME', 'TEAM_ID', 'TEAM_ABBREVIATION',
  'TEAM_NAME', 'GAME_ID', 'GAME_DATE', 'MATCHUP', 'WL', 'MIN', 'FGM', 'FGA',
  'FG_PCT', 'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA', 'FT_PCT', 'OREB', 'DREB',
  'REB', 'AST', 'TOV', 'STL', 'BLK', 'BLKA', 'PF', 'PTS', 'PLUS_MINUS',
  'NBA_FANTASY_PTS',
];
const playerFields = [
  'PLAYER_ID', 'PLAYER_NAME', 'TEAM_ID', 'TEAM_ABBREVIATION', 'TEAM_NAME',
  'POSITION', 'DRAFT_YEAR', 'DRAFT_ROUND',
];

function csvValue(value) {
  if (value === null || value === undefined) return '';
  const text = String(value);
  return /[",\n\r]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function toCsv(fields, rows) {
  return [fields, ...rows].map((row) => row.map(csvValue).join(',')).join('\n') + '\n';
}

async function getSet(url) {
  const response = await fetch(url, { headers });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}: ${url}`);
  const body = await response.json();
  return body.resultSets?.[0] ?? body.resultSet;
}

async function main() {
  const [logs, players] = await Promise.all([
    getSet('https://stats.nba.com/stats/playergamelogs?LeagueID=00&Season=2025-26&SeasonType=Regular%20Season'),
    getSet('https://stats.nba.com/stats/playerindex?LeagueID=00&Season=2026-27'),
  ]);

  const logIndex = Object.fromEntries(logs.headers.map((field, index) => [field, index]));
  const gameRows = logs.rowSet.map((row) => gameLogFields.map((field) => row[logIndex[field]]));

  const playerIndex = Object.fromEntries(players.headers.map((field, index) => [field, index]));
  const playerRows = players.rowSet.map((row) => [
    row[playerIndex.PERSON_ID],
    `${row[playerIndex.PLAYER_FIRST_NAME]} ${row[playerIndex.PLAYER_LAST_NAME]}`.trim(),
    row[playerIndex.TEAM_ID], row[playerIndex.TEAM_ABBREVIATION], row[playerIndex.TEAM_NAME],
    row[playerIndex.POSITION], row[playerIndex.DRAFT_YEAR], row[playerIndex.DRAFT_ROUND],
  ]);

  await fs.writeFile('./data/gamelogs_2025_Reg.txt', toCsv(gameLogFields, gameRows));
  await fs.writeFile('./data/players_2026.txt', toCsv(playerFields, playerRows));
  console.log(`Saved ${gameRows.length} game logs and ${playerRows.length} player-index rows.`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
