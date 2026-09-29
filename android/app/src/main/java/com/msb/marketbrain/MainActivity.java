package com.msb.marketbrain;

import android.app.Activity;
import android.app.AlertDialog;
import android.os.Bundle;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.Toast;
import android.graphics.Bitmap;
import java.net.HttpURLConnection;
import java.net.URL;

public class MainActivity extends Activity {
  private WebView web;
  private String base;
  @Override public void onCreate(Bundle state) {
    super.onCreate(state);
    web = new WebView(this);
    web.getSettings().setJavaScriptEnabled(true);
    web.getSettings().setDomStorageEnabled(true);
    web.setWebViewClient(new WebViewClient());
    setContentView(web);
    base = getPreferences(0).getString("api", "");
    if (base.isEmpty()) askAddress(); else checkAndOpen();
  }
  private void askAddress() {
    EditText input = new EditText(this);
    input.setSingleLine(true);
    input.setHint("https://your-msb-server.example");
    new AlertDialog.Builder(this).setTitle("اتصال به موتور MSB")
      .setMessage("نشانی سرور فعال MSB را وارد کنید (HTTPS).")
      .setView(input).setCancelable(false)
      .setPositiveButton("اتصال", (d,w) -> {
        base = input.getText().toString().trim().replaceAll("/+$", "");
        if (!base.startsWith("https://")) { Toast.makeText(this,"نشانی باید با https:// شروع شود",Toast.LENGTH_LONG).show(); askAddress(); return; }
        getPreferences(0).edit().putString("api",base).apply(); checkAndOpen();
      }).show();
  }
  private void checkAndOpen() {
    new Thread(() -> {
      boolean ok = false;
      try {
        HttpURLConnection c=(HttpURLConnection)new URL(base+"/health").openConnection();
        c.setConnectTimeout(10000); c.setReadTimeout(10000);
        ok=c.getResponseCode()==200; c.disconnect();
      } catch(Exception ignored) {}
      final boolean healthy=ok;
      runOnUiThread(() -> {
        if (!healthy) {
          new AlertDialog.Builder(this).setTitle("اتصال برقرار نشد")
            .setMessage("سرور پاسخ معتبر /health نداد. نشانی را بررسی کنید.")
            .setPositiveButton("تلاش دوباره", (d,w)->checkAndOpen())
            .setNegativeButton("تغییر نشانی", (d,w)->askAddress()).show();
        } else web.loadUrl(base+"/");
      });
    }).start();
  }
  @Override public void onBackPressed() { if(web.canGoBack()) web.goBack(); else super.onBackPressed(); }
}
