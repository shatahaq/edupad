# Deep Dive: Storage Engines, Indexing, and Concurrency

Sumber: https://kelas.usu.ac.id/mod/page/view.php?id=213190

Core Architecture Module

## Database Engine Internals & Concurrency Control

Understand how modern database engines process queries, index records, and guarantee ACID properties.

### 1. Storage Engine Architecture

The storage engine coordinates disk I/O, buffer pool caching, and data serialization:

- **Buffer Pool:** In-memory cache holding data pages and dirty buffers to reduce disk reads/writes.
- **Write-Ahead Logging (WAL):** Append-only log ensuring Durability by persisting transactions before modifying data files.

### 2. Index Structures: B+ Trees vs. LSM-Trees

**B+ Tree Indexes**

Optimized for read-heavy workloads with balanced tree depths and sequential leaf node scans (e.g., InnoDB, PostgreSQL B-Tree).

**LSM-Trees (Log-Structured)**

Optimized for high-throughput write operations with in-memory MemTables flushed to immutable SSTables (e.g., RocksDB, Cassandra).

**⚠️ Concurrency & Isolation Levels:**

Multi-Version Concurrency Control (MVCC) enables non-blocking reads by maintaining snapshot versions of rows, mitigating dirty reads and phantom reads depending on the configured isolation level (Read Committed, Repeatable Read, Serializable).
