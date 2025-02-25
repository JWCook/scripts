curl -v 'https://api.us-east-1.gallery.ecr.aws/describeImageTags' \
    --data '{"registryAliasName":"aws-dynamodb-local","repositoryName":"aws-dynamodb-local"}' \
    | jq


# curl 'https://api.us-east-1.gallery.ecr.aws/describeImageTags' \
#   -H 'accept: */*' \
#   -H 'accept-language: en-US,en;q=0.9' \
#   -H 'content-type: application/json' \
#   -H 'origin: https://gallery.ecr.aws' \
#   -H 'priority: u=1, i' \
#   -H 'referer: https://gallery.ecr.aws/' \
#   -H 'sec-ch-ua: "Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"' \
#   -H 'sec-ch-ua-mobile: ?0' \
#   -H 'sec-ch-ua-platform: "Linux"' \
#   -H 'sec-fetch-dest: empty' \
#   -H 'sec-fetch-mode: cors' \
#   -H 'sec-fetch-site: same-site' \
#   -H 'user-agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36' \
#   --data-raw '{"registryAliasName":"aws-dynamodb-local","repositoryName":"aws-dynamodb-local"}'
