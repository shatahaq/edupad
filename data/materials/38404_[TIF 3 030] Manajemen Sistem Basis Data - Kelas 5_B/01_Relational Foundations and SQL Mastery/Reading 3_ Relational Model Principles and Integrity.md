# Reading 3: Relational Model Principles and Integrity

Sumber: https://kelas.usu.ac.id/mod/page/view.php?id=213106

Module 1 • Reading

## The Relational Database Model & Integrity Rules

The Relational Model represents data as mathematical relations (tables) composed of attributes (columns) and tuples (rows). It is grounded in first-order predicate logic.

**🔑 Fundamental Integrity Constraints:**

- **Domain Integrity:** Enforces that all values in a column strictly satisfy defined data types and ranges.
- **Entity Integrity:** Primary keys must be unique and cannot contain `NULL` values.
- **Referential Integrity:** Foreign key references must always point to a valid, existing tuple in the referenced relation or be set explicitly to NULL.

### Relational Normalization Essentials

Normalization reduces redundancy and update anomalies through structured forms: **1NF** (atomic values), **2NF** (no partial dependency), and **3NF/BCNF** (no transitive functional dependencies).
