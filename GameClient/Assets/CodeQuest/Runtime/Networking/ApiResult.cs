namespace CodeQuest.Networking
{
    public sealed class ApiResult<T>
    {
        public bool IsSuccess { get; private set; }
        public T Value { get; private set; }
        public ApiErrorDto Error { get; private set; }
        public long StatusCode { get; private set; }

        private ApiResult(bool success, T value, ApiErrorDto error, long statusCode)
        {
            IsSuccess = success;
            Value = value;
            Error = error;
            StatusCode = statusCode;
        }

        public static ApiResult<T> Success(T value, long statusCode) => new ApiResult<T>(true, value, null, statusCode);
        public static ApiResult<T> Failure(ApiErrorDto error, long statusCode) => new ApiResult<T>(false, default, error, statusCode);
    }
}
