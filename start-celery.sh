#!/bin/bash
celery -A musycdjango worker -l info -c 5
