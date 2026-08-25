import { indexer, createEffect, S } from "envio";
import { createPublicClient, http, erc20Abi, getAddress } from "viem";

const ZERO = "0x0000000000000000000000000000000000000000";
const DAY = 86_400;

const client = createPublicClient({
  transport: http(
    process.env.ENVIO_RPC_URL ?? "https://rpc.mainnet.chain.robinhood.com",
  ),
});

// decimals is the one field the Deployed event doesn't carry. The Effect API
// batches, memoises and caches it, so each token is read once for the whole sync.
const getDecimals = createEffect(
  {
    name: "getDecimals",
    input: S.string,
    output: S.number,
    cache: true,
    rateLimit: { calls: 5, per: "second" },
  },
  async ({ input }) =>
    client.readContract({
      address: getAddress(input),
      abi: erc20Abi,
      functionName: "decimals",
    }),
);

// Discover every tokenised asset from the factory instead of hardcoding a list.
indexer.contractRegister(
  { contract: "StockFactory", event: "Deployed" },
  async ({ event, context }) => {
    context.chain.StockToken.add(event.params.stock);
  },
);

// The same event carries the metadata, so no lookup is needed for name or symbol.
indexer.onEvent(
  { contract: "StockFactory", event: "Deployed" },
  async ({ event, context }) => {
    const decimals = await context.effect(getDecimals, event.params.stock);
    context.StockToken.set({
      id: event.params.stock,
      symbol: event.params.symbol,
      name: event.params.name,
      decimals,
      transferCount: 0n,
      totalVolume: 0n,
      holderCount: 0,
      firstBlock: BigInt(event.block.number),
      lastBlock: BigInt(event.block.number),
    });
  },
);

indexer.onEvent(
  { contract: "StockToken", event: "Transfer" },
  async ({ event, context }) => {
    const tokenId = event.srcAddress;
    const { from, to, value } = event.params;
    const blockNumber = BigInt(event.block.number);
    const day = Math.floor(event.block.timestamp / DAY);

    const senderId = `${tokenId}-${from}`;
    const receiverId = `${tokenId}-${to}`;
    const [token, sender, receiver] = await Promise.all([
      context.StockToken.get(tokenId),
      from === ZERO ? undefined : context.TokenBalance.get(senderId),
      to === ZERO ? undefined : context.TokenBalance.get(receiverId),
    ]);
    if (!token) return; // transfer from a contract the factory never deployed

    let holderDelta = 0;

    if (from !== ZERO) {
      const before = sender?.balance ?? 0n;
      const after = before - value;
      if (before > 0n && after <= 0n) holderDelta -= 1;
      context.TokenBalance.set({
        id: senderId,
        token_id: tokenId,
        account: from,
        balance: after,
        transferCount: (sender?.transferCount ?? 0n) + 1n,
      });
    }

    if (to !== ZERO) {
      const before = receiver?.balance ?? 0n;
      const after = before + value;
      if (before <= 0n && after > 0n) holderDelta += 1;
      context.TokenBalance.set({
        id: receiverId,
        token_id: tokenId,
        account: to,
        balance: after,
        transferCount: (receiver?.transferCount ?? 0n) + 1n,
      });
    }

    context.StockToken.set({
      ...token,
      transferCount: token.transferCount + 1n,
      totalVolume: token.totalVolume + value,
      holderCount: token.holderCount + holderDelta,
      lastBlock: blockNumber,
    });

    const statId = `${tokenId}-${day}`;
    const stat = await context.DailyTokenStat.getOrCreate({
      id: statId,
      token_id: tokenId,
      day,
      volume: 0n,
      transfers: 0,
    });
    context.DailyTokenStat.set({
      ...stat,
      volume: stat.volume + value,
      transfers: stat.transfers + 1,
    });
  },
);
