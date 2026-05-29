# Tp37HXfekNo | Lecture2Graph Notes

- Source language: Hindi
- Engine: rules
- Concepts: 10
- Dependencies: 19
- Watch: https://www.youtube.com/watch?v=Tp37HXfekNo

## Learning Path

1. [Database](https://www.youtube.com/watch?v=Tp37HXfekNo&t=6s)
   - An organized system for storing and retrieving structured data.
2. [Null](https://www.youtube.com/watch?v=Tp37HXfekNo&t=6s)
   - A marker representing missing or unknown data.
3. [Unique Constraint](https://www.youtube.com/watch?v=Tp37HXfekNo&t=6s)
   - A rule that prevents duplicate values in one or more columns.
4. [Not Null](https://www.youtube.com/watch?v=Tp37HXfekNo&t=6s)
   - A constraint that forbids missing values.
5. [Relation](https://www.youtube.com/watch?v=Tp37HXfekNo&t=73s)
   - A table-like structure in the relational model.
6. [SQL](https://www.youtube.com/watch?v=Tp37HXfekNo&t=27s)
   - The standard query language used to work with relational databases.
7. [Attribute](https://www.youtube.com/watch?v=Tp37HXfekNo&t=73s)
   - A column or property in a relation.
8. [Candidate Key](https://www.youtube.com/watch?v=Tp37HXfekNo&t=23s)
   - A minimal set of attributes that uniquely identifies each tuple.
9. [Primary Key](https://www.youtube.com/watch?v=Tp37HXfekNo&t=0s)
   - The chosen candidate key used as the main identifier for rows.
10. [Normalization](https://www.youtube.com/watch?v=Tp37HXfekNo&t=27s)
   - A design process that reduces redundancy and anomalies in relational schemas.

## Concepts

### Primary Key
- Mentions: 191
- First seen: 00:00
- Description: The chosen candidate key used as the main identifier for rows.
- Prerequisites: Not Null, Candidate Key, Unique Constraint
- Unlocks: Normalization
- Timestamps: [00:00](https://www.youtube.com/watch?v=Tp37HXfekNo&t=0s), [00:06](https://www.youtube.com/watch?v=Tp37HXfekNo&t=6s), [00:09](https://www.youtube.com/watch?v=Tp37HXfekNo&t=9s), [00:10](https://www.youtube.com/watch?v=Tp37HXfekNo&t=10s), [00:14](https://www.youtube.com/watch?v=Tp37HXfekNo&t=14s), [00:18](https://www.youtube.com/watch?v=Tp37HXfekNo&t=18s)

### Database
- Mentions: 13
- First seen: 00:06
- Description: An organized system for storing and retrieving structured data.
- Unlocks: Relation, SQL
- Timestamps: [00:06](https://www.youtube.com/watch?v=Tp37HXfekNo&t=6s), [02:13](https://www.youtube.com/watch?v=Tp37HXfekNo&t=133s), [02:17](https://www.youtube.com/watch?v=Tp37HXfekNo&t=137s), [04:31](https://www.youtube.com/watch?v=Tp37HXfekNo&t=271s), [05:25](https://www.youtube.com/watch?v=Tp37HXfekNo&t=325s), [06:04](https://www.youtube.com/watch?v=Tp37HXfekNo&t=364s)

### Not Null
- Mentions: 123
- First seen: 00:06
- Description: A constraint that forbids missing values.
- Prerequisites: Null
- Unlocks: Primary Key, Relation, Attribute
- Timestamps: [00:06](https://www.youtube.com/watch?v=Tp37HXfekNo&t=6s), [00:50](https://www.youtube.com/watch?v=Tp37HXfekNo&t=50s), [01:01](https://www.youtube.com/watch?v=Tp37HXfekNo&t=61s), [01:24](https://www.youtube.com/watch?v=Tp37HXfekNo&t=84s), [01:28](https://www.youtube.com/watch?v=Tp37HXfekNo&t=88s), [01:29](https://www.youtube.com/watch?v=Tp37HXfekNo&t=89s)

### Unique Constraint
- Mentions: 108
- First seen: 00:06
- Description: A rule that prevents duplicate values in one or more columns.
- Unlocks: Candidate Key, Primary Key, Relation, Attribute
- Timestamps: [00:06](https://www.youtube.com/watch?v=Tp37HXfekNo&t=6s), [00:10](https://www.youtube.com/watch?v=Tp37HXfekNo&t=10s), [00:38](https://www.youtube.com/watch?v=Tp37HXfekNo&t=38s), [00:40](https://www.youtube.com/watch?v=Tp37HXfekNo&t=40s), [00:42](https://www.youtube.com/watch?v=Tp37HXfekNo&t=42s), [00:53](https://www.youtube.com/watch?v=Tp37HXfekNo&t=53s)

### Null
- Mentions: 127
- First seen: 00:06
- Description: A marker representing missing or unknown data.
- Unlocks: Not Null, Relation, Attribute
- Timestamps: [00:06](https://www.youtube.com/watch?v=Tp37HXfekNo&t=6s), [00:50](https://www.youtube.com/watch?v=Tp37HXfekNo&t=50s), [01:01](https://www.youtube.com/watch?v=Tp37HXfekNo&t=61s), [01:24](https://www.youtube.com/watch?v=Tp37HXfekNo&t=84s), [01:28](https://www.youtube.com/watch?v=Tp37HXfekNo&t=88s), [01:29](https://www.youtube.com/watch?v=Tp37HXfekNo&t=89s)

### Candidate Key
- Mentions: 6
- First seen: 00:23
- Description: A minimal set of attributes that uniquely identifies each tuple.
- Prerequisites: Attribute, Unique Constraint
- Unlocks: Primary Key
- Timestamps: [00:23](https://www.youtube.com/watch?v=Tp37HXfekNo&t=23s), [03:46](https://www.youtube.com/watch?v=Tp37HXfekNo&t=226s), [03:54](https://www.youtube.com/watch?v=Tp37HXfekNo&t=234s), [07:41](https://www.youtube.com/watch?v=Tp37HXfekNo&t=461s), [09:49](https://www.youtube.com/watch?v=Tp37HXfekNo&t=589s), [10:46](https://www.youtube.com/watch?v=Tp37HXfekNo&t=646s)

### SQL
- Mentions: 2
- First seen: 00:27
- Description: The standard query language used to work with relational databases.
- Prerequisites: Database, Relation
- Unlocks: Attribute
- Timestamps: [00:27](https://www.youtube.com/watch?v=Tp37HXfekNo&t=27s), [10:28](https://www.youtube.com/watch?v=Tp37HXfekNo&t=628s)

### Normalization
- Mentions: 1
- First seen: 00:27
- Description: A design process that reduces redundancy and anomalies in relational schemas.
- Prerequisites: Relation, Primary Key
- Timestamps: [00:27](https://www.youtube.com/watch?v=Tp37HXfekNo&t=27s)

### Relation
- Mentions: 2
- First seen: 01:13
- Description: A table-like structure in the relational model.
- Prerequisites: Database, Not Null, Unique Constraint, Null
- Unlocks: Attribute, Normalization, SQL
- Timestamps: [01:13](https://www.youtube.com/watch?v=Tp37HXfekNo&t=73s), [01:20](https://www.youtube.com/watch?v=Tp37HXfekNo&t=80s)

### Attribute
- Mentions: 10
- First seen: 01:13
- Description: A column or property in a relation.
- Prerequisites: Relation, Not Null, Unique Constraint, Null, SQL
- Unlocks: Candidate Key
- Timestamps: [01:13](https://www.youtube.com/watch?v=Tp37HXfekNo&t=73s), [02:17](https://www.youtube.com/watch?v=Tp37HXfekNo&t=137s), [02:54](https://www.youtube.com/watch?v=Tp37HXfekNo&t=174s), [03:36](https://www.youtube.com/watch?v=Tp37HXfekNo&t=216s), [03:46](https://www.youtube.com/watch?v=Tp37HXfekNo&t=226s), [03:54](https://www.youtube.com/watch?v=Tp37HXfekNo&t=234s)
