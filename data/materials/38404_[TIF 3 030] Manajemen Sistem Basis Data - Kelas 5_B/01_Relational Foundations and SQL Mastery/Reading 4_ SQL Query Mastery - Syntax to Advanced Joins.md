# Reading 4: SQL Query Mastery - Syntax to Advanced Joins

Sumber: https://kelas.usu.ac.id/mod/page/view.php?id=213107

Module 1 • Reading

## SQL Query Mastery: DDL, DML, and Advanced Joins

Structured Query Language (SQL) is the standard declarative interface for relational databases. Mastery requires understanding both semantic writing and physical query execution order.

**⚡ Logical Query Processing Order:**

Unlike procedural languages, SQL executes clauses in this specific sequence:

FROM → ON → JOIN → WHERE → GROUP BY → HAVING → SELECT → DISTINCT → ORDER BY → LIMIT

### Essential Query Patterns

- **Multi-Table Joins:** Combining `INNER`, `LEFT OUTER`, and `FULL OUTER` joins for relational synthesis.
- **Aggregation & Grouping:** Utilizing `GROUP BY` with aggregate functions and `HAVING` filters.
- **Correlated Subqueries & CTEs:** Writing modular Common Table Expressions (`WITH` clauses) for maintainable, high-performance querying.
