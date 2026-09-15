# Robinhood Stock Indexer

A [HyperIndex](https://docs.envio.dev/docs/HyperIndex/overview) indexer for the tokenized
equities and ETFs on [Robinhood Chain](https://docs.robinhood.com/chain) (chain ID `4663`).

It tracks every `Transfer` on every tokenized asset issued on the chain and
produces per-token aggregates, per-account net flows, and daily activity, exposed as GraphQL.

The full walkthrough is in [How to Index Every Tokenized Asset on Robinhood Chain](https://docs.envio.dev/blog/index-robinhood-chain-data).

## Requirements

- Node.js 22 or newer (HyperIndex auto-loads handlers with `fs.promises.glob`)
- Docker running
- An Envio API token from https://envio.dev/app/api-tokens

## Run it

```bash
pnpm install
pnpm codegen
ENVIO_API_TOKEN=<your-token> pnpm dev
```

If the install stops with `ERR_PNPM_IGNORED_BUILDS` for esbuild, run
`pnpm approve-builds esbuild`, then continue.

A GraphQL playground opens on http://localhost:8080.

## Entities

| Entity | What it holds |
| --- | --- |
| `StockToken` | Per-token symbol, name, decimals, transfer count, total volume, active account count |
| `TokenFlow` | Net movement and transfer count per account, per token |
| `DailyTokenStat` | Daily transfer count and volume per token |

## How the token list was found

Robinhood's [assets API](https://docs.robinhood.com/chain/stock-token-apis/) lists the active
tokens, but every Robinhood tokenized asset is deployed by one factory at `0x4783C67b63dE2B358Ac5951a7D41F47A38F3C046`, which emits a
creation event carrying the token address, name and symbol. Reading that factory's full
log history through HyperSync gives every address it has deployed, including some that
are not in the API. See `scripts/` for the queries.

## Notes

- HyperSync is the default data source for chain `4663`, so no RPC is configured.
- Token metadata is read once per token through the
  [Effect API](https://docs.envio.dev/docs/HyperIndex/effect-api), which batches, memoises
  and caches the call so it is not repeated per event.
- The schema stores aggregates rather than one row per transfer, which keeps the dataset
  bounded.
