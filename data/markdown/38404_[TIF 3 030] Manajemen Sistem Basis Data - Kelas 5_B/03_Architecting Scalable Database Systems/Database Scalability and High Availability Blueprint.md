---
course_id: "38404"
course: "[TIF 3 030] Manajemen Sistem Basis Data - Kelas 5/B"
pertemuan: 3
section: "Architecting Scalable Database Systems"
section_index: 3
title: "Database Scalability and High Availability Blueprint"
type: "page"
source_file: "38404_[TIF 3 030] Manajemen Sistem Basis Data - Kelas 5_B/03_Architecting Scalable Database Systems/Database Scalability and High Availability Blueprint.md"
source_url: "https://kelas.usu.ac.id/mod/page/view.php?id=213196"
activity_url: "https://kelas.usu.ac.id/mod/page/view.php?id=213196"
converter: "salin"
---

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
