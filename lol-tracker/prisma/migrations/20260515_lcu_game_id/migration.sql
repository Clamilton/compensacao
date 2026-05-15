-- AlterTable Match
ALTER TABLE "Match" ADD COLUMN "lcuGameId" TEXT;

-- CreateIndex
CREATE UNIQUE INDEX "Match_lcuGameId_key" ON "Match"("lcuGameId");
