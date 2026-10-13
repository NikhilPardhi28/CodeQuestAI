using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace CodeQuest.Networking
{
    /// <summary>Windows desktop OIDC Authorization Code + PKCE provider for the local Keycloak realm.</summary>
    public sealed class WindowsKeycloakTokenProvider : IInteractiveAuthenticationProvider, IDisposable
    {
        public const string Issuer = "http://localhost:8080/realms/codequest-dev";
        public const string ClientId = "codequest-unity";
        public const int CallbackPort = 49173;
        public const string CallbackPath = "/oidc/callback/";
        public static readonly string RedirectUri = $"http://127.0.0.1:{CallbackPort}{CallbackPath}";

        private const string CredentialTarget = "CodeQuestAI/OIDC/codequest-dev/codequest-unity";
        private static readonly Uri AuthorizeEndpoint = new Uri(Issuer + "/protocol/openid-connect/auth");
        private static readonly Uri TokenEndpoint = new Uri(Issuer + "/protocol/openid-connect/token");
        private readonly SemaphoreSlim _refreshGate = new SemaphoreSlim(1, 1);
        private string _accessToken;
        private string _refreshToken;
        private DateTimeOffset _accessTokenExpiresAt;
        private bool _disposed;

        public WindowsKeycloakTokenProvider()
        {
            _refreshToken = WindowsCredentialStore.Read(CredentialTarget);
        }

        public bool IsSignedIn => !string.IsNullOrEmpty(_accessToken) && DateTimeOffset.UtcNow < _accessTokenExpiresAt;

        public async Task<string> GetAccessTokenAsync(CancellationToken cancellationToken)
        {
            ThrowIfDisposed();
            if (IsSignedIn && _accessTokenExpiresAt > DateTimeOffset.UtcNow.AddSeconds(60)) return _accessToken;
            await _refreshGate.WaitAsync(cancellationToken);
            try
            {
                if (IsSignedIn && _accessTokenExpiresAt > DateTimeOffset.UtcNow.AddSeconds(60)) return _accessToken;
                if (string.IsNullOrEmpty(_refreshToken)) return null;
                var response = await RequestTokenAsync(new Dictionary<string, string>
                {
                    ["grant_type"] = "refresh_token",
                    ["client_id"] = ClientId,
                    ["refresh_token"] = _refreshToken
                }, cancellationToken);
                if (response == null)
                {
                    _accessToken = null;
                    _accessTokenExpiresAt = DateTimeOffset.MinValue;
                    return null;
                }
                return AcceptTokenResponse(response) ? _accessToken : null;
            }
            finally { _refreshGate.Release(); }
        }

        public async Task<bool> SignInAsync(CancellationToken cancellationToken)
        {
            ThrowIfDisposed();
            using (var loginTimeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken))
            {
                loginTimeout.CancelAfter(TimeSpan.FromMinutes(3));
                var state = Base64Url(RandomBytes(32));
                var verifier = Base64Url(RandomBytes(32));
                var challenge = CreateCodeChallenge(verifier);
                var listener = new TcpListener(System.Net.IPAddress.Loopback, CallbackPort);
                listener.Start(1);
                try
                {
                    var authorizeUrl = BuildAuthorizationUri(state, challenge);
                    Process.Start(new ProcessStartInfo(authorizeUrl) { UseShellExecute = true });
                    var callback = await ReceiveCallbackAsync(listener, loginTimeout.Token);
                    string code;
                    string callbackError;
                    if (!TryValidateCallback(callback, state, out code, out callbackError) || !string.IsNullOrEmpty(callbackError)) return false;
                    var response = await RequestTokenAsync(new Dictionary<string, string>
                    {
                        ["grant_type"] = "authorization_code",
                        ["client_id"] = ClientId,
                        ["redirect_uri"] = RedirectUri,
                        ["code"] = code,
                        ["code_verifier"] = verifier
                    }, loginTimeout.Token);
                    return response != null && AcceptTokenResponse(response);
                }
                finally { listener.Stop(); }
            }
        }

        public void Dispose()
        {
            if (_disposed) return;
            _disposed = true;
            _accessToken = null;
            _refreshToken = null;
            _refreshGate.Dispose();
        }

        public static string CreateCodeChallenge(string verifier)
        {
            using (var sha = SHA256.Create()) return Base64Url(sha.ComputeHash(Encoding.ASCII.GetBytes(verifier)));
        }

        public static string BuildAuthorizationUri(string state, string challenge)
        {
            var query = "response_type=code&client_id=" + Uri.EscapeDataString(ClientId) +
                        "&redirect_uri=" + Uri.EscapeDataString(RedirectUri) +
                        "&scope=" + Uri.EscapeDataString("openid profile") +
                        "&state=" + Uri.EscapeDataString(state) +
                        "&code_challenge=" + Uri.EscapeDataString(challenge) +
                        "&code_challenge_method=S256";
            return AuthorizeEndpoint + "?" + query;
        }

        public static bool TryValidateCallback(string requestTarget, string expectedState, out string code, out string error)
        {
            code = null;
            error = null;
            if (string.IsNullOrEmpty(requestTarget) || !requestTarget.StartsWith(CallbackPath + "?", StringComparison.Ordinal)) return false;
            var values = ParseQuery(requestTarget.Substring(CallbackPath.Length + 1));
            if (values == null || !values.TryGetValue("state", out var state) || !FixedTimeEquals(state, expectedState)) return false;
            if (values.TryGetValue("error", out error)) return false;
            return values.TryGetValue("code", out code) && !string.IsNullOrWhiteSpace(code) && code.Length <= 4096;
        }

        private static Task<string> ReceiveCallbackAsync(TcpListener listener, CancellationToken cancellationToken)
        {
            return Task.Run(() =>
            {
                using (cancellationToken.Register(listener.Stop))
                using (var client = listener.AcceptTcpClient())
                {
                    client.ReceiveTimeout = 10000;
                    using (var stream = client.GetStream())
                    using (var reader = new StreamReader(stream, Encoding.ASCII, false, 1024, true))
                    {
                        stream.ReadTimeout = 10000;
                        var requestLine = reader.ReadLine();
                        if (requestLine == null || requestLine.Length > 8192) throw new InvalidDataException("Callback request exceeded the limit.");
                        var headerBytes = 0;
                        string host = null;
                        var hostCount = 0;
                        string line;
                        while (!string.IsNullOrEmpty(line = reader.ReadLine()))
                        {
                            headerBytes += line.Length;
                            if (headerBytes > 8192) throw new InvalidDataException("Callback headers exceeded the limit.");
                            if (line.StartsWith("Host:", StringComparison.OrdinalIgnoreCase))
                            {
                                hostCount++;
                                host = line.Substring(5).Trim();
                            }
                        }
                        var parts = requestLine.Split(' ');
                        var expectedHost = "127.0.0.1:" + CallbackPort.ToString(CultureInfo.InvariantCulture);
                        var target = parts.Length == 3 && parts[0] == "GET" && parts[2].StartsWith("HTTP/1.", StringComparison.Ordinal) ? parts[1] : null;
                        var safeTarget = hostCount == 1 && host == expectedHost && target != null ? target : null;
                        var responseBody = Encoding.UTF8.GetBytes("<!doctype html><title>CodeQuest sign-in</title><p>Sign-in response received. You may return to CodeQuest.</p>");
                        var headers = Encoding.ASCII.GetBytes("HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nCache-Control: no-store\r\nConnection: close\r\nContent-Length: " + responseBody.Length + "\r\n\r\n");
                        stream.Write(headers, 0, headers.Length);
                        stream.Write(responseBody, 0, responseBody.Length);
                        stream.Flush();
                        return safeTarget;
                    }
                }
            }, cancellationToken);
        }

        private static async Task<TokenResponse> RequestTokenAsync(Dictionary<string, string> form, CancellationToken cancellationToken)
        {
            return await Task.Run(() =>
            {
                cancellationToken.ThrowIfCancellationRequested();
                try
                {
                    var encoded = new StringBuilder();
                    foreach (var pair in form)
                    {
                        if (encoded.Length > 0) encoded.Append('&');
                        encoded.Append(Uri.EscapeDataString(pair.Key)).Append('=').Append(Uri.EscapeDataString(pair.Value));
                    }
                    var request = (HttpWebRequest)WebRequest.Create(TokenEndpoint);
                    request.Method = "POST";
                    request.ContentType = "application/x-www-form-urlencoded";
                    request.Timeout = 10000;
                    request.ReadWriteTimeout = 10000;
                    request.AllowAutoRedirect = false;
                    var bytes = Encoding.UTF8.GetBytes(encoded.ToString());
                    request.ContentLength = bytes.Length;
                    using (var stream = request.GetRequestStream()) stream.Write(bytes, 0, bytes.Length);
                    using (var response = (HttpWebResponse)request.GetResponse())
                    {
                        if (response.StatusCode != HttpStatusCode.OK) return null;
                        using (var reader = new StreamReader(response.GetResponseStream()))
                        {
                            var json = reader.ReadToEnd();
                            if (json.Length > 32768) return null;
                            return UnityEngine.JsonUtility.FromJson<TokenResponse>(json);
                        }
                    }
                }
                catch (WebException) { return null; }
                catch (IOException) { return null; }
            }, cancellationToken).ConfigureAwait(false);
        }

        private bool AcceptTokenResponse(TokenResponse response)
        {
            if (response == null || !IsTokenResponseAcceptable(response.access_token, response.token_type, response.refresh_token, response.expires_in))
            {
                _accessToken = null;
                _accessTokenExpiresAt = DateTimeOffset.MinValue;
                return false;
            }
            if (!WindowsCredentialStore.Write(CredentialTarget, response.refresh_token)) return false;
            _refreshToken = response.refresh_token;
            _accessToken = response.access_token;
            _accessTokenExpiresAt = DateTimeOffset.UtcNow.AddSeconds(response.expires_in);
            return true;
        }

        private void ThrowIfDisposed()
        {
            if (_disposed) throw new ObjectDisposedException(nameof(WindowsKeycloakTokenProvider));
        }

        private static byte[] RandomBytes(int count)
        {
            var bytes = new byte[count];
            using (var rng = RandomNumberGenerator.Create()) rng.GetBytes(bytes);
            return bytes;
        }

        private static string Base64Url(byte[] bytes) => Convert.ToBase64String(bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_');

        public static bool IsTokenLifetimeAcceptable(int expiresIn) => expiresIn >= 60 && expiresIn <= 86400;

        public static bool IsTokenResponseAcceptable(string accessToken, string tokenType, string refreshToken, int expiresIn) =>
            !string.IsNullOrWhiteSpace(accessToken) &&
            string.Equals(tokenType, "Bearer", StringComparison.OrdinalIgnoreCase) &&
            !string.IsNullOrWhiteSpace(refreshToken) && IsTokenLifetimeAcceptable(expiresIn);

        private static bool FixedTimeEquals(string left, string right)
        {
            if (left == null || right == null) return false;
            var a = Encoding.UTF8.GetBytes(left);
            var b = Encoding.UTF8.GetBytes(right);
            var difference = a.Length ^ b.Length;
            for (var i = 0; i < Math.Min(a.Length, b.Length); i++) difference |= a[i] ^ b[i];
            return difference == 0;
        }

        private static Dictionary<string, string> ParseQuery(string query)
        {
            var result = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (var field in query.Split('&'))
            {
                var pair = field.Split(new[] { '=' }, 2);
                if (pair.Length != 2) return null;
                string key;
                string value;
                try
                {
                    key = Uri.UnescapeDataString(pair[0].Replace('+', ' '));
                    value = Uri.UnescapeDataString(pair[1].Replace('+', ' '));
                }
                catch (UriFormatException) { return null; }
                if (result.ContainsKey(key)) return null;
                result[key] = value;
            }
            return result;
        }

        [Serializable]
        private sealed class TokenResponse
        {
            public string access_token = null;
            public string refresh_token = null;
            public string token_type = null;
            public int expires_in = 0;
        }
    }

    internal static class WindowsCredentialStore
    {
        private const uint GenericCredential = 1;
        private const uint PersistLocalMachine = 2;

        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        private struct NativeCredential
        {
            public uint Flags;
            public uint Type;
            public string TargetName;
            public string Comment;
            public long LastWritten;
            public uint CredentialBlobSize;
            public IntPtr CredentialBlob;
            public uint Persist;
            public uint AttributeCount;
            public IntPtr Attributes;
            public string TargetAlias;
            public string UserName;
        }

        [DllImport("Advapi32.dll", EntryPoint = "CredWriteW", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool CredWrite(ref NativeCredential credential, uint flags);
        [DllImport("Advapi32.dll", EntryPoint = "CredReadW", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool CredRead(string target, uint type, uint flags, out IntPtr credential);
        [DllImport("Advapi32.dll", EntryPoint = "CredDeleteW", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool CredDelete(string target, uint type, uint flags);
        [DllImport("Advapi32.dll", SetLastError = false)]
        private static extern void CredFree(IntPtr credential);

        internal static bool Write(string target, string secret)
        {
            var data = Encoding.UTF8.GetBytes(secret);
            var blob = Marshal.AllocHGlobal(data.Length);
            try
            {
                Marshal.Copy(data, 0, blob, data.Length);
                var credential = new NativeCredential
                {
                    Type = GenericCredential,
                    TargetName = target,
                    UserName = "codequest-unity",
                    CredentialBlob = blob,
                    CredentialBlobSize = (uint)data.Length,
                    Persist = PersistLocalMachine
                };
                return CredWrite(ref credential, 0);
            }
            finally
            {
                Array.Clear(data, 0, data.Length);
                for (var i = 0; i < data.Length; i++) Marshal.WriteByte(blob, i, 0);
                Marshal.FreeHGlobal(blob);
            }
        }

        internal static string Read(string target)
        {
            if (!CredRead(target, GenericCredential, 0, out var pointer)) return null;
            try
            {
                var credential = Marshal.PtrToStructure<NativeCredential>(pointer);
                if (credential.CredentialBlob == IntPtr.Zero || credential.CredentialBlobSize == 0 || credential.CredentialBlobSize > 16384) return null;
                var data = new byte[(int)credential.CredentialBlobSize];
                Marshal.Copy(credential.CredentialBlob, data, 0, data.Length);
                try { return Encoding.UTF8.GetString(data); }
                finally { Array.Clear(data, 0, data.Length); }
            }
            finally { CredFree(pointer); }
        }
    }
}
