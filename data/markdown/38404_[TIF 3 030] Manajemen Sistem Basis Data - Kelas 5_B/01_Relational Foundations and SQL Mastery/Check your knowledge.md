---
course_id: "38404"
course: "[TIF 3 030] Manajemen Sistem Basis Data - Kelas 5/B"
pertemuan: 1
section: "Relational Foundations and SQL Mastery"
section_index: 1
title: "Check your knowledge"
type: "page"
source_file: "38404_[TIF 3 030] Manajemen Sistem Basis Data - Kelas 5_B/01_Relational Foundations and SQL Mastery/Check your knowledge.md"
source_url: "https://kelas.usu.ac.id/mod/page/view.php?id=195401"
activity_url: "https://kelas.usu.ac.id/mod/page/view.php?id=195401"
converter: "salin"
---

# Check your knowledge

Sumber: https://kelas.usu.ac.id/mod/page/view.php?id=195401

Database Schema Reference
supabase-schema-zokpxifcjmfrwsmlgegs.jpg

![Database Schema](https://placehold.co/800x600/1e293b/ffffff?text=Schema+Image+Not+Found
(Ensure+image+is+in+same+folder))

## 1. High-Value Customers

1 / 10

Write a query to find the top 5 customers who have spent the most money across all their completed orders. Return their `full_name` and the total amount spent.

A.

```
SELECT c.full_name, SUM(o.total_amount) AS total_spent
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.full_name
ORDER BY total_spent DESC
LIMIT 5;
```

B.

```
SELECT c.full_name, SUM(o.total_amount) AS total_spent
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.status = 'Completed'
GROUP BY c.customer_id, c.full_name
ORDER BY total_spent DESC
LIMIT 5;
```

C.

```
SELECT c.full_name, MAX(o.total_amount) AS total_spent
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.status = 'Completed'
GROUP BY c.customer_id, c.full_name
ORDER BY total_spent ASC
LIMIT 5;
```

D.

```
SELECT c.full_name, SUM(o.total_amount) AS total_spent
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE o.status = 'Completed'
ORDER BY total_spent DESC
LIMIT 5;
```

Check Answer

← Previous
Next →
