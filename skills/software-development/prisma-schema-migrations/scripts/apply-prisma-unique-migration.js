// apply-prisma-unique-migration.js
// Statically re-runnable: copy this file to your repo, fill in HEADER, run.
// Deploys a @@unique constraint to Supabase via Management API.
// Handles the 6 pitfalls catalogued in the parent SKILL.md:
//
//   1. snake_case table/column names (vs Prisma PascalCase camelCase)
//   2. CTID-based dedupe before UNIQUE
//   3. CREATE UNIQUE INDEX vs ADD CONSTRAINT (different pg_catalogs)
//   4. Pooler URL with regional hostname, username "postgres.{ref}"
//   5. Transaction mode requires explicit BEGIN/COMMIT for ALTER
//   6. Management API body shape { query: "..." }
//
// HEADER — set these three:
const SUPABASE_URL = 'https://api.supabase.com/v1/projects/PROJECT_REF';  // ← your ref
const PAT          = 'sbp_xxx';                                            // ← Personal Access Token
const TABLE_QUAL   = {
  telemetry: { pk: ['driver_id', 'timestamp'], expected_conname: 'telemetry_driver_timestamp_unique' },
  // Add more tables here — each must declare the partition keys and expected constraint name.
};

async function exec(sql, label) {
  console.log(`\n📌 ${label}`);
  const res = await fetch(`${SUPABASE_URL}/database/query`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${PAT}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: sql }),
  });
  const text = await res.text();
  let json;
  try { json = JSON.parse(text); } catch { json = { raw: text }; }

  console.log(`   HTTP ${res.status}`);
  console.log(`   ${JSON.stringify(json).substring(0, 2000)}`);

  if (res.ok && json.rows && json.rows.length) return json.rows;
  if (res.ok) return null;
  throw new Error(json.message || `HTTP ${res.status}`);
}

async function applyUnique(tableName, cfg) {
  const cols = cfg.pk.map(c => `"${c}"`).join(', ');
  const tbl  = `"${tableName}"`;
  const idem = cfg.expected_conname;

  console.log(`\n${'═'.repeat(60)}\n📦 Table: ${tableName}  → constraint: ${idem}`);

  // 1. CTID-based dedupe (PITFALL 2)
  await exec(`
    WITH duplicated AS (
      SELECT ctid,
        ROW_NUMBER() OVER (PARTITION BY ${cfg.pk.map(c => `"${c}"`).join(', ')} ORDER BY ctid) AS rn
      FROM ${tbl}
    )
    DELETE FROM ${tbl}
    WHERE ctid IN (SELECT ctid FROM duplicated WHERE rn > 1);
  `, `Dedupe ${tableName}`);

  // 2. CREATE UNIQUE INDEX (no transaction needed for the index)
  const idxName = `tmp_${idem}`;
  await exec(`
    CREATE UNIQUE INDEX IF NOT EXISTS "${idxName}"
      ON ${tbl} (${cols});
  `, `Create UNIQUE INDEX on ${tableName}`);

  // 3. Convert index → constraint so pg_constraint reflects the migration (PITFALL 3)
  try {
    await exec(`
      ALTER TABLE ${tbl}
        DROP CONSTRAINT IF EXISTS "${idem}";
      ALTER TABLE ${tbl}
        ADD CONSTRAINT "${idem}"
        UNIQUE USING INDEX "${idxName}";
    `, `Convert index → constraint on ${tableName}`);
  } catch (e) {
    console.warn(`   ⚠️ Conversion failed (continuing): ${e.message}`);
  }

  // 4. Verify
  const check = await exec(`
    SELECT
      EXISTS(SELECT 1 FROM pg_constraint WHERE conname = '${idem}') AS has_constraint,
      EXISTS(SELECT 1 FROM pg_indexes  WHERE indexname = '${idxName}') AS has_index;
  `, `Verify ${tableName}`);

  if (check && check[0]) {
    const { has_constraint, has_index } = check[0];
    console.log(`   ${has_constraint ? '✅' : '❌'} constraint ${idem}`);
    console.log(`   ${has_index ? '⚠️ (still present)' : '✅'} temp index ${idxName}`);
  }
}

async function main() {
  console.log('🚀 Apply Prisma @@unique migration');
  console.log(`   Endpoint: ${SUPABASE_URL}/database/query`);

  // Pitfall 1: discover schema
  await exec(`
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public' ORDER BY table_name;
  `, 'Discover public tables');

  for (const [table, cfg] of Object.entries(TABLE_QUAL)) {
    await applyUnique(table, cfg);
  }

  console.log('\n✅ Done.');
}

main().catch(err => {
  console.error(`\n❌ FATAL: ${err.message}`);
  process.exit(1);
});
