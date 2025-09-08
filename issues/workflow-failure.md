## Workflow Failure Issue

**Description**: The workflow is currently failing because it uses a deprecated version of `actions/upload-artifact@v3`. 

**Suggested Solution**: Update to `actions/upload-artifact@v4` in `.github/workflows/browser-tests.yml`.

**Reference**: 75848afd3346bd6e286cf9bee7ea2fc2459eab08

**Error Log**: 
`This request has been automatically failed because it uses a deprecated version of actions/upload-artifact: v3.`
