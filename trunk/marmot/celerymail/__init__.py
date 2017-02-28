from .tasks import send_html_mail_task


def send_html_mail(subject, html_content, recipient_list):
    return send_html_mail_task.delay(subject, html_content, recipient_list)
