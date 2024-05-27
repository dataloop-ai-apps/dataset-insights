python -m uvicorn "app:app" \
        --reload \
        --host="0.0.0.0" \
        --port=5463 \
        --timeout-keep-alive=60 \
        &

cp /tmp/app/nginx.conf /etc/nginx/conf.d
npm run dev &

nginx -g 'daemon off;'
