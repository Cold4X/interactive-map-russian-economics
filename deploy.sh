#!/bin/bash
#!/bin/bash
echo "Running deployment script..."

# Установка зависимостей для Dash
pip install dash plotly pandas

# Даем права на выполнение самому себе (не обязательно, но для порядка)
chmod +x deploy.sh

# Дополнительные команды если нужны
# python manage.py migrate
# python manage.py collectstatic --noinput