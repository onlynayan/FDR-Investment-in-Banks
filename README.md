# FDR Investment in Banks

Developed by Nayan

## Live Project

http://103.163.97.33:8000/

## Project Overview

This repository contains the working codebase for the **FDR Investment in Banks** platform.  
It focuses on extracting and scoring bank report indicators, running eligibility scans, and showing live run progress in a browser dashboard.

## Current Modules in This Repo

- `ui_server.py`: backend server for UI, live run status, process control, and API endpoints.
- `scraper.py`: extraction pipeline for bank report indicators and scorecard output.
- `eligible_scraper.py`: eligibility scan pipeline and output generation.
- `apex_client.py`: eligibility data integration payload handling.
- `apex_performance_client.py`: performance data integration payload handling.
- `ui/`: frontend dashboard, live run modal, progress view, and scorecard interface.
- `config/`: project configuration inputs used by pipeline components.

## Current Scope

- Live extraction and eligibility execution from the UI.
- Background run state tracking and process controls.
- UI progress visualization for both scraper flows.
- Output generation for bank analysis workflows.

## Planned Additions

- Database table scripts.
- Additional API modules and integration endpoints.
