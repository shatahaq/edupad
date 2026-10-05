# Reading 1: Foundations of Database Management Systems

Sumber: https://kelas.usu.ac.id/mod/page/view.php?id=213104

Module 1 • Reading

## Foundations of Database Management Systems

A **Database Management System (DBMS)** is system software for creating, managing, and governing structured data. Unlike traditional file systems, a DBMS guarantees data integrity, concurrency control, and multi-user access isolation.

**📌 Core Architectural Pillars:**

- **Data Abstraction:** Three-schema architecture (Physical, Logical, and View levels).
- **Data Independence:** Logical and physical data independence insulating applications from storage layout shifts.
- **ACID Properties:** Atomicity, Consistency, Isolation, and Durability ensuring transactional reliability.

### Key Components of a DBMS

The core engine consists of the *Query Processor* (parser, optimizer, execution engine) and the *Storage Manager* (buffer manager, transaction manager, recovery manager). Together, they translate declarative commands into high-performance disk and memory operations.
