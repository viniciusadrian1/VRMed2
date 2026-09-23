using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.SceneManagement;

internal class CommandScript : IRunCommand
{
    public void Execute(ExecutionResult result)
    {
        var atual = SceneManager.GetActiveScene();
        result.Log("Editor conectado: Unity " + Application.unityVersion + "; cena ativa: " + atual.name + "; alterações pendentes: " + atual.isDirty);
        // Valores reais do layout R3F. Unity é apenas bancada, nunca runtime.
        Vector3 olhos = new Vector3(0, 1.6f, 2.55f);
        Vector3 painel = new Vector3(0.85f, 1.45f, -0.65f);
        Vector3 orgao = new Vector3(-1.05f, 1.5f, -0.5f);
        float painelDistancia = Vector3.Distance(olhos, painel);
        float anguloPainel = Mathf.Atan2(painel.x, olhos.z - painel.z) * Mathf.Rad2Deg;
        float anguloOrgao = Mathf.Atan2(orgao.x, olhos.z - orgao.z) * Mathf.Rad2Deg;
        result.Log("Escala em metros; olhos = " + olhos + "; centro do console = " + painel + "; centro do órgão = " + orgao);
        result.Log("Distância olhos-console = " + painelDistancia.ToString("F3") + "m; azimute console = " + anguloPainel.ToString("F1") + " graus; azimute órgão = " + anguloOrgao.ToString("F1") + " graus.");
        var banco = EditorSceneManager.NewPreviewScene();
        try
        {
            System.Action<string, Vector3, Vector3, Color> bloco = (nome, pos, tamanho, cor) => {
                var obj = GameObject.CreatePrimitive(PrimitiveType.Cube);
                result.RegisterObjectCreation(obj);
                obj.name = nome;
                SceneManager.MoveGameObjectToScene(obj, banco);
                // glTF/Three usa -Z à frente; converte para a convenção Unity.
                obj.transform.position = new Vector3(pos.x, pos.y, -pos.z);
                obj.transform.localScale = tamanho;
                var shader = Shader.Find("Universal Render Pipeline/Unlit") ?? Shader.Find("Unlit/Color");
                var mat = new Material(shader);
                result.RegisterObjectCreation(mat);
                mat.color = cor;
                obj.GetComponent<Renderer>().sharedMaterial = mat;
            };
            bloco("Piso", new Vector3(0, -0.03f, 0), new Vector3(9.2f, 0.05f, 9.2f), new Color(.13f,.22f,.26f));
            bloco("Console / volume de interação", painel + new Vector3(0,-.2f,0), new Vector3(1.84f,2.02f,.17f), new Color(.16f,.43f,.53f));
            bloco("Órgão / volume máximo, não anatomia", orgao, new Vector3(1.02f,1.02f,1.02f), new Color(.76f,.62f,.43f));
            bloco("Bancada / tampo 85 cm", new Vector3(-1.05f,.42f,-.5f), new Vector3(1.22f,.84f,1.07f), new Color(.39f,.55f,.55f));
            bloco("Letreiro", new Vector3(0,2.81f,-3.22f), new Vector3(2.5f,.84f,.16f), new Color(.10f,.24f,.31f));
            var cameraObj = new GameObject("Validação / olhos a 1,60m");
            result.RegisterObjectCreation(cameraObj);
            SceneManager.MoveGameObjectToScene(cameraObj, banco);
            var cam = cameraObj.AddComponent<Camera>();
            cam.transform.position = new Vector3(olhos.x, olhos.y, -olhos.z);
            cam.transform.LookAt(new Vector3(0,1.45f,.6f));
            cam.fieldOfView = 65;
            cam.scene = banco;
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(.04f,.08f,.10f);
            var rt = new RenderTexture(1200,800,24);
            var textura = new Texture2D(1200,800,TextureFormat.RGB24,false);
            var antes = RenderTexture.active;
            try {
                cam.targetTexture = rt;
                cam.Render();
                RenderTexture.active = rt;
                textura.ReadPixels(new Rect(0,0,1200,800),0,0);
                textura.Apply();
                var pasta = @"C:\Users\vinic\Downloads\InnerVision\vrmed\docs\evidencias-arena";
                System.IO.Directory.CreateDirectory(pasta);
                System.IO.File.WriteAllBytes(System.IO.Path.Combine(pasta,"unity-escala.png"), textura.EncodeToPNG());
                result.Log("Captura de blockout salva em docs/evidencias-arena/unity-escala.png. Não é teste de headset nem de performance WebXR.");
            } finally {
                RenderTexture.active = antes;
                cam.targetTexture = null;
                Object.DestroyImmediate(textura);
                rt.Release(); Object.DestroyImmediate(rt);
            }
        }
        finally { EditorSceneManager.ClosePreviewScene(banco); }
        result.Log("Cena de trabalho preservada: " + SceneManager.GetActiveScene().name);
    }
}
