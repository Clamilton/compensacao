-- AlterTable Match
ALTER TABLE "Match" ADD COLUMN "duration" INTEGER;
ALTER TABLE "Match" ADD COLUMN "source" TEXT NOT NULL DEFAULT 'manual';

-- AlterTable MatchPlayer
ALTER TABLE "MatchPlayer" ADD COLUMN "champion"    TEXT;
ALTER TABLE "MatchPlayer" ADD COLUMN "kills"       INTEGER;
ALTER TABLE "MatchPlayer" ADD COLUMN "deaths"      INTEGER;
ALTER TABLE "MatchPlayer" ADD COLUMN "assists"     INTEGER;
ALTER TABLE "MatchPlayer" ADD COLUMN "gold"        INTEGER;
ALTER TABLE "MatchPlayer" ADD COLUMN "damage"      INTEGER;
ALTER TABLE "MatchPlayer" ADD COLUMN "healing"     INTEGER;
ALTER TABLE "MatchPlayer" ADD COLUMN "wardsPlaced" INTEGER;
ALTER TABLE "MatchPlayer" ADD COLUMN "wardsKilled" INTEGER;
ALTER TABLE "MatchPlayer" ADD COLUMN "cs"          INTEGER;
ALTER TABLE "MatchPlayer" ADD COLUMN "visionScore" INTEGER;
