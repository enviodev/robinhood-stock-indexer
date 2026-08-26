# Robinhood Stock Indexer

A [HyperIndex](https://docs.envio.dev/docs/HyperIndex/overview) indexer for the tokenized
equities and ETFs on [Robinhood Chain](https://docs.robinhood.com/chain) (chain ID `4663`).

It tracks every `Transfer` on all 203 tokenized assets issued on the chain and
produces per-token aggregates, per-account net flows, and daily activity, exposed as GraphQL.

## Requirements

- Node.js 22 or newer (HyperIndex v3 auto-loads handlers with `fs.promises.glob`)
- Docker running
- An Envio API token from https://envio.dev/app/api-tokens

## Run it

```bash
pnpm install
pnpm codegen
ENVIO_API_TOKEN=<your-token> pnpm dev
```

A GraphQL playground opens on http://localhost:8080.

## Entities

| Entity | What it holds |
| --- | --- |
| `StockToken` | Per-token symbol, name, decimals, transfer count, total volume, active account count |
| `TokenFlow` | Net movement and transfer count per account, per token |
| `DailyTokenStat` | Daily transfer count and volume per token |

## How the token list was found

There is no published token list for these contracts. Every Robinhood tokenized asset is
deployed by one factory at `0x4783C67b63dE2B358Ac5951a7D41F47A38F3C046`, which emits a
creation event carrying the token address, name and symbol. Reading that factory's full
log history through HyperSync gives all 203 addresses, verified against on-chain
`symbol()` calls. See `scripts/` for the queries.

## Notes

- HyperSync is the default data source for chain `4663`, so no RPC is configured.
- Token metadata is read once per token through the
  [Effect API](https://docs.envio.dev/docs/HyperIndex/effect-api), which batches, memoises
  and caches the call so it is not repeated per event.
- The schema stores aggregates rather than one row per transfer, which keeps the dataset
  bounded.
