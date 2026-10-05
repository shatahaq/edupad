---
course_id: "38404"
course: "[TIF 3 030] Manajemen Sistem Basis Data - Kelas 5/B"
pertemuan: 1
section: "Relational Foundations and SQL Mastery"
section_index: 1
title: "Reading 3: Relational Model Principles and Integrity"
type: "page"
source_file: "38404_[TIF 3 030] Manajemen Sistem Basis Data - Kelas 5_B/01_Relational Foundations and SQL Mastery/Reading 3_ Relational Model Principles and Integrity.md"
source_url: "https://kelas.usu.ac.id/mod/page/view.php?id=213106"
activity_url: "https://kelas.usu.ac.id/mod/page/view.php?id=213106"
converter: "salin"
---

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
