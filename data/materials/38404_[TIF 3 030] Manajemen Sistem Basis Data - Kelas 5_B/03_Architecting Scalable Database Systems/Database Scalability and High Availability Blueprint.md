# Database Scalability and High Availability Blueprint

Sumber: https://kelas.usu.ac.id/mod/page/view.php?id=213196

## 🏛️ Scalable Database Architecture & HA

Mastering production-grade database systems: scaling, replication, partitioning, and resilience.

### 1. Replication Strategies

Production systems rely on data redundancy to balance read loads and ensure disaster recovery:

- **Primary-Replica (Leader-Follower):** Write queries target the primary node; changes propagate asynchronously or synchronously to read replicas.
- **Multi-Primary (Master-Master):** Multiple nodes handle writes, requiring robust distributed conflict resolution mechanisms.

**📌 Key Takeaway:** Synchronous replication guarantees zero data loss (RPO = 0) at the cost of write latency, while asynchronous replication minimizes write latency with slight replication lag.

### 2. Sharding & Partitioning

When vertical scaling reaches its physical limit, database partitioning divides massive datasets across storage nodes:

- **Horizontal Sharding:** Splitting rows across databases using hash-based, range-based, or directory-based shard keys.
- **Vertical Partitioning:** Splitting column families or domain-specific tables into decoupled microservices databases.

**⚠️ Warning:** Avoid cross-shard joins and distributed multi-shard transactions whenever possible to prevent severe network overhead and latency spikes.
