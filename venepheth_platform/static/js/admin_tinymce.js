document.addEventListener("DOMContentLoaded", function() {
    if (typeof tinymce !== 'undefined') {
        tinymce.init({
            selector: 'textarea[name="content_raw"], textarea[name="description"], textarea[name="abstract"]',
            height: 400,
            menubar: false,
            plugins: [
                'advlist', 'autolink', 'lists', 'link', 'image', 'charmap', 'preview',
                'anchor', 'searchreplace', 'visualblocks', 'code', 'fullscreen',
                'insertdatetime', 'media', 'table', 'help', 'wordcount'
            ],
            toolbar: 'undo redo | blocks | ' +
            'bold italic backcolor | alignleft aligncenter ' +
            'alignright alignjustify | bullist numlist outdent indent | ' +
            'link image media | removeformat | code | help',
            content_style: 'body { font-family:Inter,Helvetica,Arial,sans-serif; font-size:16px; color: #1E3A5F; }'
        });
    }
});
