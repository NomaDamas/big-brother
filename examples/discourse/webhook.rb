require "net/http"

upload_path = ENV.fetch("DISCOURSE_UPLOAD_PATH")
uri = URI("http://localhost:8080/v1/scan")
request = Net::HTTP::Post.new(uri)
form = [["image", File.open(upload_path, "rb"), { filename: File.basename(upload_path) }]]
request.set_form(form, "multipart/form-data")

response = Net::HTTP.start(uri.hostname, uri.port) { |http| http.request(request) }
abort("blocked by big-brother") if response.body.include?('"decision":"blocked"')
