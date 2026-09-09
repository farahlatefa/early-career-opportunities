# Early Career Opportunities

A public, searchable dashboard for internships and entry-level full-time opportunities.

## Filters
- Internship / Full-Time
- Location (city, country, region, remote/hybrid/on-site)
- Application deadline
- Reports to
- Sector
- Work arrangement
- Free-text search and sorting

## Sectors
Biology & Life Sciences; Consulting; Data & Analytics; Finance; Healthcare; Humanitarian / NGO; International Development; Marketing & Communications; Operations; Policy / Government; Procurement; Research; Sales / Business Development; Sports; Supply Chain; Sustainability / ESG; Technology / IT.

## Automatic updates
`.github/workflows/update-jobs.yml` runs the collector hourly. The scanner is not limited to a fixed company whitelist. It ingests public job sources and, when configured, Adzuna's broad job-search API across multiple countries.

### Optional broad-search setup
For significantly broader coverage, create a free/paid Adzuna developer account and add these repository secrets under **Settings → Secrets and variables → Actions**:
- `ADZUNA_APP_ID`
- `ADZUNA_APP_KEY`

The workflow currently queries the US, UK, and Canada. Add country codes in `ADZUNA_COUNTRIES` in the workflow if your API plan supports them.

## Important limitation
No scraper can reliably cover literally every company on the internet. Some employers block automated access, require logins, use unsupported ATS systems, or do not expose deadlines/reporting lines. This project is designed to aggregate as broadly as permitted public sources and APIs allow, without maintaining a company whitelist.

Each displayed opportunity has an **Open application** link taken from its source listing. Users should verify the final employer/application page before submitting personal information.
