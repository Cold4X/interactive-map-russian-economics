#!/bin/bash
echo "Running deployment script..."

# Установка зависимостей для Dash
pip install dash plotly pandas dash-leaflet dash-extensions

# Дополнительные команды если нужны
# python manage.py migrate
# python manage.py collectstatic --noinput