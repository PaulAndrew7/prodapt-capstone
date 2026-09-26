---
policy: md
version: v1
title: Model Development Standard
category: Data science
business_area: Pricing
owner: Head of Actuarial Modelling
effective_from: 2026-02-01
effective_to:
status: published
---

# 1 Scope
This standard applies to statistical and machine-learning models used to price Kestrel Mutual products.

# 2 Data

## 2.1 Approved data sources
Model training may use only data sources that are listed in the model’s data specification and approved by the data owner.

## 2.2 Training data retention
Datasets used to train a pricing model are kept for the life of that model plus three years, so that its outputs can be reproduced.

## 2.3 Direct identifiers
Direct identifiers such as names, email addresses and phone numbers must be removed from training datasets unless the model’s data specification records why they are needed.

# 3 Validation

## 3.1 Independent validation
Before a pricing model goes live, a validator who did not build it must review its performance and fairness tests.

## 3.2 Monitoring
Live pricing models are monitored monthly. A model whose monitored error exceeds the tolerance in its specification for two consecutive months must be reviewed by its validator.
