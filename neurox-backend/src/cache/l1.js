// ═══════════════════════════════════════════════════════
// L1 Cache — In-memory LRU cache layer
// Falls back to Redis L2, or database as L3
// ═══════════════════════════════════════════════════════
import { Redis } from "@upstash/redis";
import { createClient } from "@supabase/supabase-js";

const redisUrl = process.env.UPSTASH_REDIS_REST_URL;
const redisToken = process.env.UPSTASH_REDIS_REST_TOKEN;

const redisClient = redisUrl && redisToken
  ? new Redis({ url: redisUrl, token: redisToken })
  : null;

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_KEY;

const supabase = supabaseUrl && supabaseKey
  ? createClient(supabaseUrl, supabaseKey)
  : null;

class LRUCache {
  constructor(maxSize = 500) {
    this.maxSize = maxSize;
    this.cache = new Map();
    this.ttls = new Map();
  }

  get(key) {
    const value = this.cache.get(key);
    const ttl = this.ttls.get(key);

    if (!value || (ttl && Date.now() > ttl)) {
      this.cache.delete(key);
      this.ttls.delete(key);
      return null;
    }

    this.cache.delete(key);
    this.cache.set(key, value);
    return value;
  }

  set(key, value, ttlMs = 300000) {
    if (this.cache.size >= this.maxSize && !this.cache.has(key)) {
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
      this.ttls.delete(firstKey);
    }

    this.cache.set(key, value);
    this.ttls.set(key, Date.now() + ttlMs);
  }

  delete(key) {
    this.cache.delete(key);
    this.ttls.delete(key);
  }

  clear() {
    this.cache.clear();
    this.ttls.clear();
  }
}

const l1Cache = new LRUCache(500);

async function getCachedScan(scanId) {
  const l1Key = `scan:${scanId}`;

  const cached = l1Cache.get(l1Key);
  if (cached) {
    return { data: cached, source: "L1" };
  }

  if (redisClient) {
    const redisKey = `cache:${l1Key}`;
    const cached = await redisClient.get(redisKey);
    if (cached) {
      l1Cache.set(l1Key, cached, 300000);
      return { data: cached, source: "L2" };
    }
  }

  if (supabase) {
    const { data, error } = await supabase
      .from("scans")
      .select("*")
      .eq("scan_id", scanId)
      .single();

    if (!error && data) {
      l1Cache.set(l1Key, data, 300000);
      if (redisClient) {
        await redisClient.set(`cache:${l1Key}`, data, { ex: 600 });
      }
      return { data, source: "L3" };
    }
  }

  return { data: null, source: null };
}

async function setCachedScan(scanId, data, ttlMs = 600000) {
  const l1Key = `scan:${scanId}`;

  l1Cache.set(l1Key, data, ttlMs);

  if (redisClient) {
    await redisClient.set(`cache:${l1Key}`, data, { ex: Math.ceil(ttlMs / 1000) });
  }
}

function invalidateCachedScan(scanId) {
  const l1Key = `scan:${scanId}`;
  l1Cache.delete(l1Key);
}

export { l1Cache, getCachedScan, setCachedScan, invalidateCachedScan };