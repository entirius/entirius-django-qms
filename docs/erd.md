---
title: "QMS: Database Diagrams"
description: "Auto-generated ER diagrams for the QMS module."
sidebar:
  badge:
    text: "Auto-gen"
    variant: "note"
---

:::caution[Auto-generated]
These diagrams are auto-generated from Django model introspection.
Do not edit. Run `make erd` in entirius-docker to regenerate.
:::

## Warehouse

```d2 layout=elk
Warehouse: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  code: varchar {constraint: unique}
  name: varchar
  description: text
  source_type: varchar
  is_active: bool
  last_synced_at: timestamp
}

WarehouseStock: {
  shape: sql_table
  style.fill: "#00ACC1"
  style.stroke: "#12141A"
  style.font-color: "#EBEDF2"
  id: int {constraint: primary_key}
  warehouse_id: int {constraint: foreign_key}
  sku: varchar
  quantity: int
}

Channel: {
  shape: sql_table
  style.fill: "#484B57"
  style.stroke: "#1A1C25"
  style.stroke-dash: 3
  style.font-color: "#9A9CAA"
  id: int {constraint: primary_key}
  label: "Channel (External: django_checkout)"
}



Warehouse.id <-> Channel.id: {style.stroke: "#484B57"}

WarehouseStock.warehouse_id -> Warehouse.id: {style.stroke: "#00ACC1"}
```
